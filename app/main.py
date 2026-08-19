import datetime as dt
import logging
from urllib.parse import quote

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func

from app import __version__
from app.db import (
    init_db, get_db, Subscription, SeenArticle, FREQUENCY_CHOICES, User, AppSettings,
    PendingRegistration, PasswordReset,
)
from app.scheduler import start_scheduler, poll_subscription, dispatch_subscription
from app.settings import get_settings
from app.i18n import get_translator, SUPPORTED_LANGS, LANG_NAMES, DEFAULT_LANG
from app.config import TEMPLATES_DIR, STATIC_DIR, APP_BASE_URL
from app import mailer, journal_rank, crypto
from app.auth import (
    NotAuthenticated,
    SESSION_COOKIE,
    SESSION_LIFETIME_DAYS,
    VERIFICATION_CODE_TTL,
    VERIFICATION_MAX_ATTEMPTS,
    RESEND_COOLDOWN,
    get_current_user,
    get_current_user_optional,
    hash_password,
    verify_password,
    verify_invite_code,
    is_valid_username,
    find_user_by_identifier,
    generate_code,
    hash_code,
    verify_code,
    create_session,
    delete_session,
)

logger = logging.getLogger("pubmed_alert.main")

app = FastAPI(title="PubMed Alert")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

LANG_COOKIE = "lang"
SESSION_MAX_AGE = SESSION_LIFETIME_DAYS * 24 * 60 * 60


@app.exception_handler(NotAuthenticated)
def handle_not_authenticated(request: Request, exc: NotAuthenticated):
    return RedirectResponse("/login", status_code=303)


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()
    if not mailer.is_system_mailer_configured():
        logger.warning(
            "系统发件账号未配置，注册/找回密码会失败 (system sender account not configured in "
            ".env — registration/password-reset will fail)"
        )
    if not APP_BASE_URL:
        logger.warning(
            "APP_BASE_URL 未配置，提醒邮件里不会带「选择要加入待阅读的文献」链接 (APP_BASE_URL "
            "not set in .env — alert emails won't include the reading-list picker link)"
        )


def _split_lines(text: str):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _current_lang(request: Request) -> str:
    lang = request.cookies.get(LANG_COOKIE)
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def _set_session_cookie(request: Request, resp, token: str):
    resp.set_cookie(
        SESSION_COOKIE, token,
        httponly=True, samesite="lax",
        secure=(request.url.scheme == "https"),
        max_age=SESSION_MAX_AGE,
    )
    return resp


def render(request: Request, name: str, context: dict, db, status_code: int = 200):
    lang = _current_lang(request)
    ctx = {
        **context,
        "lang": lang,
        "t": get_translator(lang),
        "langs": [(code, LANG_NAMES[code]) for code in SUPPORTED_LANGS],
        "app_version": __version__,
        "current_user": get_current_user_optional(request, db),
    }
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


@app.get("/lang/{code}")
def set_lang(code: str, request: Request):
    dest = request.headers.get("referer", "/")
    resp = RedirectResponse(dest, status_code=303)
    if code in SUPPORTED_LANGS:
        resp.set_cookie(LANG_COOKIE, code, max_age=60 * 60 * 24 * 365)
    return resp


# ---------------------------------------------------------------------------
# Auth (unprotected)
# ---------------------------------------------------------------------------

def _username_taken(db, username: str, exclude_pending_id: int = None) -> bool:
    now = dt.datetime.utcnow()
    if db.query(User).filter(func.lower(User.username) == username.lower()).first() is not None:
        return True
    query = (
        db.query(PendingRegistration)
        .filter(func.lower(PendingRegistration.username) == username.lower())
        .filter(PendingRegistration.expires_at >= now)
    )
    if exclude_pending_id is not None:
        query = query.filter(PendingRegistration.id != exclude_pending_id)
    return query.first() is not None


@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request, db=Depends(get_db)):
    return render(request, "register.html", {"error": None, "email": "", "username": ""}, db)


@app.post("/register")
def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    invite_code: str = Form(...),
    db=Depends(get_db),
):
    username = username.strip()
    email = email.strip().lower()

    def fail(error_key):
        return render(
            request, "register.html",
            {"error": error_key, "email": email, "username": username}, db, status_code=400,
        )

    if not verify_invite_code(invite_code):
        return fail("register_error_invite_code")
    if not is_valid_username(username):
        return fail("register_error_username_invalid")
    if password != password_confirm:
        return fail("register_error_password_mismatch")
    if len(password) < 8:
        return fail("register_error_weak_password")
    if db.query(User).filter_by(email=email).first() is not None:
        return fail("register_error_email_taken")
    if _username_taken(db, username):
        return fail("register_error_username_taken")
    if not mailer.is_system_mailer_configured():
        return fail("register_error_mailer_not_configured")

    # 按 email 替换旧的待验证记录——同一个人重新提交是正常行为；但绝不能按 username 匹配删除，
    # 不然可以拿自己的邮箱、填别人想要的用户名，反复提交去冲掉对方正在进行的注册（见 CLAUDE.md）。
    # Replace any prior pending row keyed by email only — resubmitting is normal for the same
    # person, but matching on username too would let someone grief another person's in-progress
    # registration by resubmitting their own email with the victim's desired username.
    db.query(PendingRegistration).filter_by(email=email).delete()

    code = generate_code()
    now = dt.datetime.utcnow()
    db.add(PendingRegistration(
        email=email, username=username, password_hash=hash_password(password),
        code_hash=hash_code(code), last_sent_at=now, expires_at=now + VERIFICATION_CODE_TTL,
    ))
    db.commit()
    mailer.send_verification_email(email, code, "register")

    return RedirectResponse(f"/register/verify?email={quote(email)}", status_code=303)


@app.get("/register/verify", response_class=HTMLResponse)
def register_verify_form(request: Request, email: str = "", db=Depends(get_db)):
    return render(request, "register_verify.html", {"error": None, "notice": None, "email": email}, db)


@app.post("/register/verify")
def register_verify_submit(
    request: Request,
    email: str = Form(...),
    code: str = Form(...),
    db=Depends(get_db),
):
    email = email.strip().lower()

    def fail(error_key):
        return render(
            request, "register_verify.html", {"error": error_key, "notice": None, "email": email},
            db, status_code=400,
        )

    pending = db.query(PendingRegistration).filter_by(email=email).order_by(
        PendingRegistration.created_at.desc()
    ).first()
    if pending is None or pending.expires_at < dt.datetime.utcnow():
        return fail("register_verify_error_expired")
    if not verify_code(code, pending.code_hash):
        pending.attempts += 1
        if pending.attempts >= VERIFICATION_MAX_ATTEMPTS:
            pending.expires_at = dt.datetime.utcnow()  # 强制过期，走"过期"分支，不用重填整个表单
        db.commit()
        return fail("register_verify_error_invalid")

    # 邮箱/用户名的唯一性在提交注册时已经检查过一次，这里验证码通过、真正建号前再查一次，防止
    # 等待验证码的这段时间里被另一次注册抢先占用。
    # Uniqueness was already checked at submission time; re-check right before creating the real
    # User, since another registration could have taken the same email/username while this one
    # was waiting on its code.
    if db.query(User).filter_by(email=email).first() is not None:
        db.delete(pending)
        db.commit()
        return fail("register_error_email_taken")
    if _username_taken(db, pending.username, exclude_pending_id=pending.id):
        db.delete(pending)
        db.commit()
        return fail("register_error_username_taken")

    # 第一个注册成功的账号，自动认领升级前遗留下来的、还没有 owner 的订阅/设置。
    # The first successfully-registered account auto-adopts any pre-existing subscriptions/
    # settings left over from before this upgrade that don't have an owner yet.
    is_first_user = db.query(User).count() == 0
    user = User(email=email, username=pending.username, password_hash=pending.password_hash)
    db.add(user)
    db.flush()
    if is_first_user:
        db.query(Subscription).filter(Subscription.user_id.is_(None)).update({"user_id": user.id})
        db.query(AppSettings).filter(AppSettings.user_id.is_(None)).update({"user_id": user.id})
    db.delete(pending)
    db.commit()

    token = create_session(db, user)
    dest = "/?adopted=1" if is_first_user else "/"
    resp = RedirectResponse(dest, status_code=303)
    return _set_session_cookie(request, resp, token)


@app.post("/register/resend")
def register_resend(request: Request, email: str = Form(...), db=Depends(get_db)):
    email = email.strip().lower()
    pending = db.query(PendingRegistration).filter_by(email=email).order_by(
        PendingRegistration.created_at.desc()
    ).first()
    if pending is None:
        return render(request, "register_verify.html", {"error": "register_verify_error_expired", "notice": None, "email": email}, db, status_code=400)

    now = dt.datetime.utcnow()
    if now - pending.last_sent_at < RESEND_COOLDOWN:
        return render(request, "register_verify.html", {"error": "verify_error_cooldown", "notice": None, "email": email}, db, status_code=400)

    code = generate_code()
    pending.code_hash = hash_code(code)
    pending.attempts = 0
    pending.last_sent_at = now
    pending.expires_at = now + VERIFICATION_CODE_TTL
    db.commit()
    mailer.send_verification_email(email, code, "register")
    return render(request, "register_verify.html", {"error": None, "notice": "verify_resent_notice", "email": email}, db)


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, db=Depends(get_db)):
    reset = request.query_params.get("reset") == "1"
    return render(request, "login.html", {"error": None, "identifier": "", "reset": reset}, db)


@app.post("/login")
def login_submit(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db),
):
    user = find_user_by_identifier(db, identifier)
    if user is None or not verify_password(password, user.password_hash):
        return render(
            request, "login.html",
            {"error": "login_error_invalid", "identifier": identifier, "reset": False}, db, status_code=400,
        )

    token = create_session(db, user)
    resp = RedirectResponse("/", status_code=303)
    return _set_session_cookie(request, resp, token)


@app.post("/logout")
def logout(request: Request, db=Depends(get_db)):
    delete_session(db, request.cookies.get(SESSION_COOKIE))
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_form(request: Request, db=Depends(get_db)):
    return render(request, "forgot_password.html", {"sent": False, "identifier": ""}, db)


@app.post("/forgot-password")
def forgot_password_submit(request: Request, identifier: str = Form(...), db=Depends(get_db)):
    user = find_user_by_identifier(db, identifier)
    # 不管账号存不存在，都显示同一句提示，不暴露某个邮箱/用户名是否注册过。
    # Show the same message regardless of whether an account was found, to avoid revealing
    # whether a given email/username is registered.
    if user is not None and mailer.is_system_mailer_configured():
        db.query(PasswordReset).filter_by(user_id=user.id).delete()
        code = generate_code()
        now = dt.datetime.utcnow()
        db.add(PasswordReset(
            user_id=user.id, code_hash=hash_code(code), last_sent_at=now,
            expires_at=now + VERIFICATION_CODE_TTL,
        ))
        db.commit()
        mailer.send_verification_email(user.email, code, "reset")

    return render(request, "forgot_password.html", {"sent": True, "identifier": identifier}, db)


@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_form(request: Request, identifier: str = "", db=Depends(get_db)):
    return render(request, "reset_password.html", {"error": None, "identifier": identifier}, db)


@app.post("/reset-password")
def reset_password_submit(
    request: Request,
    identifier: str = Form(...),
    code: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    db=Depends(get_db),
):
    def fail(error_key):
        return render(
            request, "reset_password.html", {"error": error_key, "identifier": identifier},
            db, status_code=400,
        )

    user = find_user_by_identifier(db, identifier)
    if user is None:
        return fail("reset_password_error_invalid")

    reset = db.query(PasswordReset).filter_by(user_id=user.id).order_by(
        PasswordReset.created_at.desc()
    ).first()
    if reset is None or reset.expires_at < dt.datetime.utcnow():
        return fail("reset_password_error_invalid")
    if not verify_code(code, reset.code_hash):
        reset.attempts += 1
        if reset.attempts >= VERIFICATION_MAX_ATTEMPTS:
            reset.expires_at = dt.datetime.utcnow()
        db.commit()
        return fail("reset_password_error_invalid")
    if new_password != new_password_confirm:
        return fail("account_error_mismatch")
    if len(new_password) < 8:
        return fail("account_error_weak")

    user.password_hash = hash_password(new_password)
    db.query(PasswordReset).filter_by(user_id=user.id).delete()
    db.commit()
    return RedirectResponse("/login?reset=1", status_code=303)


# ---------------------------------------------------------------------------
# Subscriptions (require login)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index(request: Request, user: User = Depends(get_current_user), db=Depends(get_db)):
    subs = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
        .all()
    )
    settings = get_settings(db, user.id)
    return render(request, "index.html", {
        "subscriptions": subs,
        "mailer_configured": mailer.is_configured(settings),
        "jcr_available": journal_rank.is_available(),
        "adopted": request.query_params.get("adopted") == "1",
    }, db)


@app.get("/subscriptions/new", response_class=HTMLResponse)
def new_subscription_form(request: Request, user: User = Depends(get_current_user), db=Depends(get_db)):
    return render(request, "form.html", {
        "sub": None,
        "frequency_choices": FREQUENCY_CHOICES,
    }, db)


@app.post("/subscriptions/new")
def create_subscription(
    label: str = Form(...),
    keywords: str = Form(""),
    journals: str = Form(""),
    authors: str = Form(""),
    query_override: str = Form(""),
    recipient_email: str = Form(...),
    frequency: str = Form("immediate"),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    sub = Subscription(
        user_id=user.id,
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


def _owned_subscription(db, sub_id: int, user: User) -> Subscription:
    sub = db.query(Subscription).filter_by(id=sub_id, user_id=user.id).first()
    if sub is None:
        raise HTTPException(status_code=404)
    return sub


@app.get("/subscriptions/{sub_id}/edit", response_class=HTMLResponse)
def edit_subscription_form(
    sub_id: int, request: Request, user: User = Depends(get_current_user), db=Depends(get_db)
):
    sub = _owned_subscription(db, sub_id, user)
    return render(request, "form.html", {
        "sub": sub,
        "frequency_choices": FREQUENCY_CHOICES,
    }, db)


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
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    sub = _owned_subscription(db, sub_id, user)
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
def toggle_subscription(sub_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    sub = _owned_subscription(db, sub_id, user)
    sub.active = not sub.active
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/subscriptions/{sub_id}/delete")
def delete_subscription(sub_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    sub = _owned_subscription(db, sub_id, user)
    db.delete(sub)
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/subscriptions/{sub_id}/poll_now")
def poll_now(sub_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    """手动立即触发一次轮询+发送，方便调试和验证配置 / manually trigger a poll+dispatch now, for testing"""
    sub = _owned_subscription(db, sub_id, user)
    settings = get_settings(db, user.id)
    poll_subscription(db, sub, settings)
    dispatch_subscription(db, sub, settings)
    return RedirectResponse(f"/subscriptions/{sub_id}/preview", status_code=303)


@app.get("/subscriptions/{sub_id}/preview", response_class=HTMLResponse)
def preview_subscription(
    sub_id: int, request: Request, user: User = Depends(get_current_user), db=Depends(get_db)
):
    sub = _owned_subscription(db, sub_id, user)
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
    }, db)


def _owned_article(db, article_id: int, user: User) -> SeenArticle:
    art = (
        db.query(SeenArticle)
        .join(Subscription, SeenArticle.subscription_id == Subscription.id)
        .filter(SeenArticle.id == article_id, Subscription.user_id == user.id)
        .first()
    )
    if art is None:
        raise HTTPException(status_code=404)
    return art


@app.post("/articles/{article_id}/save")
def toggle_save_article(article_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    art = _owned_article(db, article_id, user)
    if art.saved_for_reading:
        art.saved_for_reading = False
        art.saved_at = None
        art.read_at = None
    else:
        art.saved_for_reading = True
        art.saved_at = dt.datetime.utcnow()
    db.commit()
    return RedirectResponse(f"/subscriptions/{art.subscription_id}/preview", status_code=303)


@app.post("/articles/{article_id}/read")
def toggle_read_article(article_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    art = _owned_article(db, article_id, user)
    art.read_at = None if art.read_at else dt.datetime.utcnow()
    db.commit()
    return RedirectResponse("/reading-list", status_code=303)


@app.get("/reading-list", response_class=HTMLResponse)
def reading_list_page(request: Request, user: User = Depends(get_current_user), db=Depends(get_db)):
    articles = (
        db.query(SeenArticle)
        .join(Subscription, SeenArticle.subscription_id == Subscription.id)
        .filter(Subscription.user_id == user.id, SeenArticle.saved_for_reading.is_(True))
        .order_by(SeenArticle.read_at.isnot(None), SeenArticle.saved_at.desc())
        .all()
    )
    return render(request, "reading_list.html", {"articles": articles}, db)


@app.get("/reading-list/pick", response_class=HTMLResponse)
def reading_list_pick_form(request: Request, u: int, ids: str, t: str, db=Depends(get_db)):
    article_ids = [int(i) for i in ids.split(",") if i.strip().isdigit()]
    if not article_ids or not crypto.verify_reading_list_token(u, article_ids, t):
        return render(request, "reading_list_pick.html", {"error": True, "articles": None}, db, status_code=400)

    articles = (
        db.query(SeenArticle)
        .join(Subscription, SeenArticle.subscription_id == Subscription.id)
        .filter(SeenArticle.id.in_(article_ids), Subscription.user_id == u)
        .all()
    )
    if len(articles) != len(article_ids):
        return render(request, "reading_list_pick.html", {"error": True, "articles": None}, db, status_code=400)

    return render(request, "reading_list_pick.html", {
        "error": False, "articles": articles, "u": u, "ids": ids, "token": t, "submitted": None,
    }, db)


@app.post("/reading-list/pick")
def reading_list_pick_submit(
    request: Request,
    u: int = Form(...),
    ids: str = Form(...),
    t: str = Form(...),
    selected: list[str] = Form([]),
    db=Depends(get_db),
):
    article_ids = [int(i) for i in ids.split(",") if i.strip().isdigit()]
    if not article_ids or not crypto.verify_reading_list_token(u, article_ids, t):
        return render(request, "reading_list_pick.html", {"error": True, "articles": None}, db, status_code=400)

    selected_ids = {int(i) for i in selected if i.isdigit()} & set(article_ids)
    added = 0
    if selected_ids:
        rows = (
            db.query(SeenArticle)
            .join(Subscription, SeenArticle.subscription_id == Subscription.id)
            .filter(SeenArticle.id.in_(selected_ids), Subscription.user_id == u)
            .all()
        )
        now = dt.datetime.utcnow()
        for row in rows:
            if not row.saved_for_reading:
                row.saved_for_reading = True
                row.saved_at = now
                added += 1
        db.commit()

    return render(request, "reading_list_pick.html", {
        "error": False, "articles": None, "submitted": added,
    }, db)


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, user: User = Depends(get_current_user), db=Depends(get_db)):
    settings = get_settings(db, user.id)
    return render(request, "settings.html", {
        "settings": settings,
        "mailer_configured": mailer.is_configured(settings),
        "saved": request.query_params.get("saved") == "1",
        "test_result": request.query_params.get("test"),
        "test_error": request.query_params.get("msg", ""),
        "account_saved": request.query_params.get("account_saved") == "1",
        "account_error": request.query_params.get("account_error"),
    }, db)


@app.post("/account/change-password")
def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    def fail(error_key):
        return RedirectResponse(f"/settings?account_error={error_key}", status_code=303)

    if not verify_password(current_password, user.password_hash):
        return fail("account_error_current_wrong")
    if new_password != new_password_confirm:
        return fail("account_error_mismatch")
    if len(new_password) < 8:
        return fail("account_error_weak")

    user.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse("/settings?account_saved=1", status_code=303)


@app.post("/settings")
def save_settings(
    smtp_host: str = Form(""),
    smtp_port: int = Form(587),
    smtp_use_ssl: str = Form(""),
    sender_email: str = Form(""),
    sender_password: str = Form(""),
    ncbi_api_key: str = Form(""),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    settings = get_settings(db, user.id)
    settings.smtp_host = smtp_host.strip()
    settings.smtp_port = smtp_port
    settings.smtp_use_ssl = bool(smtp_use_ssl)
    settings.sender_email = sender_email.strip()
    if sender_password.strip():
        settings.sender_password = sender_password.strip()
    settings.ncbi_api_key = ncbi_api_key.strip()
    db.commit()
    return RedirectResponse("/settings?saved=1", status_code=303)


@app.post("/settings/test-email")
def send_test_email(
    to_email: str = Form(...), user: User = Depends(get_current_user), db=Depends(get_db)
):
    settings = get_settings(db, user.id)
    try:
        mailer.send_test_email(settings, to_email)
    except Exception as e:
        return RedirectResponse(f"/settings?test=err&msg={quote(str(e)[:200])}", status_code=303)
    return RedirectResponse("/settings?test=ok", status_code=303)
