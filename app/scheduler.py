"""
定时任务：只在每个订阅"到期该发送了"的那一刻才去检索 PubMed，而不是固定周期无差别地检索所有订阅。
Scheduled jobs: only search PubMed for a subscription at the exact moment it's due to send —
not on a blanket fixed cadence applied to every subscription regardless of its own frequency.

内部有一个很轻量的"心跳"（每 TICK_MINUTES 分钟跑一次），它只做一次便宜的数据库时间判断；
真正花钱/花时间的 PubMed 检索，只会在某个订阅确实到期时才触发。
There's a lightweight internal "heartbeat" (runs every TICK_MINUTES minutes) that only does a
cheap DB timestamp check; the actual expensive PubMed search only fires when a subscription is
actually due.

调度器跑在应用进程内部（用 APScheduler），不依赖系统 cron，方便本地和以后云端部署都能直接用。
The scheduler runs inside the app process (via APScheduler) — no system cron dependency, so it
works the same locally and later on a cloud server.
"""
import datetime as dt
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app import mailer, pubmed, journal_rank, unpaywall
from app.db import get_session, Subscription, SeenArticle, PendingRegistration, PasswordReset
from app.settings import get_settings

logger = logging.getLogger("pubmed_alert.scheduler")

TICK_JOB_ID = "check_due_subscriptions"
TICK_MINUTES = 15  # 心跳粒度，不需要用户配置 heartbeat granularity, not user-configurable

CLEANUP_JOB_ID = "cleanup_expired_auth_rows"
CLEANUP_MINUTES = 60

FREQUENCY_INTERVALS = {
    "immediate": dt.timedelta(seconds=0),
    "daily": dt.timedelta(days=1),
    "every_3_days": dt.timedelta(days=3),
    "weekly": dt.timedelta(days=7),
}

INITIAL_RELEVANT_COUNT = 10
INITIAL_RECENT_COUNT = 20
INITIAL_BACKFILL_YEARS = 5


def is_due(sub: Subscription, now: dt.datetime) -> bool:
    """判断某个订阅现在是否"到期"，该去检索并发送了。
    Whether a subscription is currently "due" to be searched and sent.

    从未发送过：一律视为到期（这样新订阅能马上拿到入门文献，见 poll_subscription）。
    Never dispatched before: always due (so a new subscription gets its starter batch right away
    — see poll_subscription).
    """
    if sub.last_dispatched_at is None:
        return True
    interval = FREQUENCY_INTERVALS.get(sub.frequency, dt.timedelta(seconds=0))
    return (now - sub.last_dispatched_at) >= interval


def poll_subscription(session, sub: Subscription, settings):
    """查询新文献并存入数据库（自动去重），不在这里发邮件
    Look up new articles and store them (auto-deduplicated); does not send email here.

    首次轮询（该订阅还从未成功轮询过）：同时查"近5年内最相关的10篇"和"不限时间最新的20篇"两批，
    合并去重后一起作为"入门文献"，每篇标记它属于哪一批（可能两批都算）。
    此后每次轮询：改为按发表日期取最新的文献，和之前一样——因为去重是按"这个订阅历史上所有见过
    的 PMID"来判断的，不管首次存了多少篇，增量轮询天然只会捞到还没见过的新文章，不需要额外记录
    "上次查到哪了"。
    First poll for this subscription (never successfully polled before): search both "10 most
    relevant from the last 5 years" and "20 most recent regardless of date", merge + dedupe them
    into the "starter" batch, tagging each article with which bucket(s) it came from. Every poll
    after that: fetch the newest articles by publication date, as before — since dedup is against
    every PMID this subscription has ever seen, the incremental poll naturally only surfaces
    genuinely new articles no matter how many the initial poll stored, with no separate watermark
    needed.
    """
    is_initial = not sub.initial_poll_done
    relevant_set, recent_set = set(), set()
    try:
        if is_initial:
            query = pubmed.build_query(sub.keywords, sub.journals, sub.authors, sub.query_override)
            relevant_pmids = pubmed.search_pmids(
                query, retmax=INITIAL_RELEVANT_COUNT, api_key=settings.ncbi_api_key,
                sort="relevance", reldate_days=INITIAL_BACKFILL_YEARS * 365,
            )
            recent_pmids = pubmed.search_pmids(
                query, retmax=INITIAL_RECENT_COUNT, api_key=settings.ncbi_api_key, sort="date",
            )
            relevant_set, recent_set = set(relevant_pmids), set(recent_pmids)
            union_pmids = list(dict.fromkeys(relevant_pmids + recent_pmids))  # 保序去重
            articles = pubmed.fetch_details(union_pmids, api_key=settings.ncbi_api_key)
        else:
            query, articles = pubmed.find_new_articles(
                keywords=sub.keywords,
                journals=sub.journals,
                authors=sub.authors,
                query_override=sub.query_override,
                api_key=settings.ncbi_api_key,
            )
    except Exception:
        logger.exception("轮询 PubMed 失败 (poll failed) for subscription %s", sub.id)
        return 0

    existing_pmids = {
        row.pmid for row in session.query(SeenArticle.pmid)
        .filter(SeenArticle.subscription_id == sub.id).all()
    }

    new_count = 0
    seen_this_batch = set()  # 防止两批检索有重叠时，同一个 pmid 被插入两次
    for art in articles:
        if art["pmid"] in existing_pmids or art["pmid"] in seen_this_batch:
            continue
        seen_this_batch.add(art["pmid"])

        rank = journal_rank.lookup(
            journal_title=art["journal"],
            issn=art.get("issn"),
            issn_linking=art.get("issn_linking"),
        )

        row = SeenArticle(
            subscription_id=sub.id,
            pmid=art["pmid"],
            title=art["title"],
            authors=art["authors"],
            journal=art["journal"],
            pub_date=art["pub_date"],
            doi=art["doi"],
            abstract=art["abstract"],
            jcr_quartile=rank["quartile"] if rank else None,
            jif=rank["jif"] if rank else None,
            initial_relevant=art["pmid"] in relevant_set,
            initial_recent=art["pmid"] in recent_set,
            oa_pdf_url=unpaywall.lookup(art["doi"]),
        )
        session.add(row)
        new_count += 1

    if is_initial:
        sub.initial_poll_done = True

    session.commit()
    return new_count


def _cross_subscription_labels(session, user_id, pmid, exclude_subscription_id):
    """同一个用户名下，除了 exclude_subscription_id 之外，还有哪些订阅也见过这个 pmid。
    用于邮件里标注"这篇文章同时匹配了你的另一个订阅"，不代表去重/漏发，两边的邮件都照常发送。

    Which of this same user's other subscriptions (besides exclude_subscription_id) have also
    seen this pmid. Used to annotate the email with "this article also matches your other
    subscription X" — this is a note only, not deduplication; both emails still get sent.
    """
    rows = (
        session.query(Subscription.label)
        .join(SeenArticle, SeenArticle.subscription_id == Subscription.id)
        .filter(
            Subscription.user_id == user_id,
            SeenArticle.pmid == pmid,
            Subscription.id != exclude_subscription_id,
        )
        .distinct()
        .all()
    )
    return [row[0] for row in rows]


def dispatch_subscription(session, sub: Subscription, settings):
    """发送该订阅当前所有"待发送"的文献；调用方负责判断是否到了该发送的时间
    Send all currently "pending" articles for this subscription; the caller is responsible for
    deciding whether it's actually due.
    """
    now = dt.datetime.utcnow()

    pending = (
        session.query(SeenArticle)
        .filter(SeenArticle.subscription_id == sub.id, SeenArticle.sent_at.is_(None))
        .order_by(SeenArticle.first_seen_at.asc())
        .all()
    )
    if not pending:
        return  # 没有新文献，不发送空邮件 no new articles, skip sending an empty email

    if not mailer.is_configured(settings):
        logger.warning("发件邮箱未配置，跳过发送 (sender account not configured, skipping send) for subscription %s", sub.id)
        return

    # 这是一个临时属性，只在这次发送时算一遍、给模板用，不会存进数据库。
    # A transient attribute computed just for this send and read by the template — never
    # persisted to the database.
    for row in pending:
        row.duplicate_labels = _cross_subscription_labels(session, sub.user_id, row.pmid, sub.id)

    try:
        mailer.send_digest(settings, sub, pending)
    except Exception:
        logger.exception("发送邮件失败 (send failed) for subscription %s", sub.id)
        return

    for row in pending:
        row.sent_at = now
    sub.last_dispatched_at = now
    session.commit()


def run_check_due():
    """心跳：只对"到期"的订阅才去检索 PubMed 并发送，其余订阅这一轮什么都不做。
    Heartbeat: only searches PubMed and sends for subscriptions that are actually "due" —
    everything else is skipped this round, at zero PubMed-request cost.

    每个订阅现在归属一个用户，要用各自归属人的发件设置，而不是一份全局设置；一次运行内按
    user_id 缓存，避免同一个用户的多个订阅重复查询。还没被认领（user_id 为空，见 main.py 的
    /register 逻辑）的订阅直接跳过，不能因为它们崩溃。
    Each subscription now belongs to a user and must use that owner's own sender settings, not
    one global settings row; cache per user_id within a single run to avoid redundant lookups for
    a user with multiple subscriptions. Not-yet-adopted subscriptions (user_id is null — see the
    /register logic in main.py) are skipped outright rather than crashing the heartbeat.
    """
    session = get_session()
    try:
        now = dt.datetime.utcnow()
        subs = (
            session.query(Subscription)
            .filter(Subscription.active.is_(True), Subscription.user_id.isnot(None))
            .all()
        )
        settings_cache = {}
        for sub in subs:
            if not is_due(sub, now):
                continue
            settings = settings_cache.get(sub.user_id)
            if settings is None:
                settings = get_settings(session, sub.user_id)
                settings_cache[sub.user_id] = settings
            n = poll_subscription(session, sub, settings)
            if n:
                logger.info("订阅 %s 发现 %d 篇新文献 (found %d new articles)", sub.label, n, n)
            dispatch_subscription(session, sub, settings)
    finally:
        session.close()


def cleanup_expired_auth_rows():
    """清掉过期的待验证注册请求/找回密码请求，避免无限堆积。
    Deletes expired pending-registration and password-reset rows so they don't accumulate forever.
    """
    session = get_session()
    try:
        now = dt.datetime.utcnow()
        session.query(PendingRegistration).filter(PendingRegistration.expires_at < now).delete()
        session.query(PasswordReset).filter(PasswordReset.expires_at < now).delete()
        session.commit()
    finally:
        session.close()


_scheduler = None


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_check_due,
        "interval",
        minutes=TICK_MINUTES,
        next_run_time=dt.datetime.now(),  # 启动时立即跑一次 run once immediately on startup
        id=TICK_JOB_ID,
        max_instances=1,
    )
    _scheduler.add_job(
        cleanup_expired_auth_rows,
        "interval",
        minutes=CLEANUP_MINUTES,
        next_run_time=dt.datetime.now(),
        id=CLEANUP_JOB_ID,
        max_instances=1,
    )
    _scheduler.start()
    return _scheduler
