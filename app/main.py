from urllib.parse import quote

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import __version__
from app.db import init_db, get_session, Subscription, SeenArticle, FREQUENCY_CHOICES
from app.scheduler import start_scheduler, poll_subscription, dispatch_subscription
from app.settings import get_settings
from app.i18n import get_translator, SUPPORTED_LANGS, LANG_NAMES, DEFAULT_LANG
from app.config import TEMPLATES_DIR, STATIC_DIR
from app import mailer, journal_rank

app = FastAPI(title="PubMed Alert")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

LANG_COOKIE = "lang"


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()


def get_db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def _split_lines(text: str):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _current_lang(request: Request) -> str:
    lang = request.cookies.get(LANG_COOKIE)
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def render(request: Request, name: str, context: dict, status_code: int = 200):
    lang = _current_lang(request)
    ctx = {
        **context,
        "lang": lang,
        "t": get_translator(lang),
        "langs": [(code, LANG_NAMES[code]) for code in SUPPORTED_LANGS],
        "app_version": __version__,
    }
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


@app.get("/lang/{code}")
def set_lang(code: str, request: Request):
    dest = request.headers.get("referer", "/")
    resp = RedirectResponse(dest, status_code=303)
    if code in SUPPORTED_LANGS:
        resp.set_cookie(LANG_COOKIE, code, max_age=60 * 60 * 24 * 365)
    return resp


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db=Depends(get_db)):
    subs = db.query(Subscription).order_by(Subscription.created_at.desc()).all()
    settings = get_settings(db)
    return render(request, "index.html", {
        "subscriptions": subs,
        "mailer_configured": mailer.is_configured(settings),
        "jcr_available": journal_rank.is_available(),
    })


@app.get("/subscriptions/new", response_class=HTMLResponse)
def new_subscription_form(request: Request):
    return render(request, "form.html", {
        "sub": None,
        "frequency_choices": FREQUENCY_CHOICES,
    })


@app.post("/subscriptions/new")
def create_subscription(
    label: str = Form(...),
    keywords: str = Form(""),
    journals: str = Form(""),
    authors: str = Form(""),
    query_override: str = Form(""),
    recipient_email: str = Form(...),
    frequency: str = Form("immediate"),
    db=Depends(get_db),
):
    sub = Subscription(
        label=label,
        recipient_email=recipient_email,
        frequency=frequency,
        query_override=query_override.strip() or None,
        active=True,
    )
    sub.keywords = _split_lines(keywords)
    sub.journals = _split_lines(journals)
    sub.authors = _split_lines(authors)
    db.add(sub)
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.get("/subscriptions/{sub_id}/edit", response_class=HTMLResponse)
def edit_subscription_form(sub_id: int, request: Request, db=Depends(get_db)):
    sub = db.query(Subscription).get(sub_id)
    return render(request, "form.html", {
        "sub": sub,
        "frequency_choices": FREQUENCY_CHOICES,
    })


@app.post("/subscriptions/{sub_id}/edit")
def update_subscription(
    sub_id: int,
    label: str = Form(...),
    keywords: str = Form(""),
    journals: str = Form(""),
    authors: str = Form(""),
    query_override: str = Form(""),
    recipient_email: str = Form(...),
    frequency: str = Form("immediate"),
    db=Depends(get_db),
):
    sub = db.query(Subscription).get(sub_id)
    sub.label = label
    sub.keywords = _split_lines(keywords)
    sub.journals = _split_lines(journals)
    sub.authors = _split_lines(authors)
    sub.query_override = query_override.strip() or None
    sub.recipient_email = recipient_email
    sub.frequency = frequency
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/subscriptions/{sub_id}/toggle")
def toggle_subscription(sub_id: int, db=Depends(get_db)):
    sub = db.query(Subscription).get(sub_id)
    sub.active = not sub.active
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/subscriptions/{sub_id}/delete")
def delete_subscription(sub_id: int, db=Depends(get_db)):
    sub = db.query(Subscription).get(sub_id)
    db.delete(sub)
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/subscriptions/{sub_id}/poll_now")
def poll_now(sub_id: int, db=Depends(get_db)):
    """手动立即触发一次轮询+发送，方便调试和验证配置 / manually trigger a poll+dispatch now, for testing"""
    settings = get_settings(db)
    sub = db.query(Subscription).get(sub_id)
    poll_subscription(db, sub, settings)
    dispatch_subscription(db, sub, settings)
    return RedirectResponse(f"/subscriptions/{sub_id}/preview", status_code=303)


@app.get("/subscriptions/{sub_id}/preview", response_class=HTMLResponse)
def preview_subscription(sub_id: int, request: Request, db=Depends(get_db)):
    sub = db.query(Subscription).get(sub_id)
    articles = (
        db.query(SeenArticle)
        .filter(SeenArticle.subscription_id == sub_id)
        .order_by(SeenArticle.first_seen_at.desc())
        .limit(100)
        .all()
    )
    return render(request, "preview.html", {
        "sub": sub,
        "articles": articles,
    })


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db=Depends(get_db)):
    settings = get_settings(db)
    return render(request, "settings.html", {
        "settings": settings,
        "mailer_configured": mailer.is_configured(settings),
        "saved": request.query_params.get("saved") == "1",
        "test_result": request.query_params.get("test"),
        "test_error": request.query_params.get("msg", ""),
    })


@app.post("/settings")
def save_settings(
    gmail_address: str = Form(""),
    gmail_app_password: str = Form(""),
    ncbi_api_key: str = Form(""),
    db=Depends(get_db),
):
    settings = get_settings(db)
    settings.gmail_address = gmail_address.strip()
    if gmail_app_password.strip():
        settings.gmail_app_password = gmail_app_password.strip()
    settings.ncbi_api_key = ncbi_api_key.strip()
    db.commit()
    return RedirectResponse("/settings?saved=1", status_code=303)


@app.post("/settings/test-email")
def send_test_email(to_email: str = Form(...), db=Depends(get_db)):
    settings = get_settings(db)
    try:
        mailer.send_test_email(settings, to_email)
    except Exception as e:
        return RedirectResponse(f"/settings?test=err&msg={quote(str(e)[:200])}", status_code=303)
    return RedirectResponse("/settings?test=ok", status_code=303)
