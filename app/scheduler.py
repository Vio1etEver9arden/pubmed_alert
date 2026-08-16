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

from app import mailer, pubmed, journal_rank
from app.db import get_session, Subscription, SeenArticle
from app.settings import get_settings

logger = logging.getLogger("pubmed_alert.scheduler")

TICK_JOB_ID = "check_due_subscriptions"
TICK_MINUTES = 15  # 心跳粒度，不需要用户配置 heartbeat granularity, not user-configurable

FREQUENCY_INTERVALS = {
    "immediate": dt.timedelta(seconds=0),
    "daily": dt.timedelta(days=1),
    "every_3_days": dt.timedelta(days=3),
    "weekly": dt.timedelta(days=7),
}

INITIAL_BACKFILL_COUNT = 10
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

    首次轮询（该订阅还从未成功轮询过）：按相关度取近5年内最相关的10篇作为"入门文献"。
    此后每次轮询：改为按发表日期取最新的文献，和之前一样。
    First poll for this subscription (never successfully polled before): fetch the 10 most
    relevant articles from the last 5 years, sorted by relevance, as a "starter" batch.
    Every poll after that: fetch the newest articles by publication date, as before.
    """
    is_initial = not sub.initial_poll_done
    try:
        if is_initial:
            query, articles = pubmed.find_new_articles(
                keywords=sub.keywords,
                journals=sub.journals,
                authors=sub.authors,
                query_override=sub.query_override,
                api_key=settings.ncbi_api_key,
                sort="relevance",
                retmax=INITIAL_BACKFILL_COUNT,
                reldate_days=INITIAL_BACKFILL_YEARS * 365,
            )
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
    for art in articles:
        if art["pmid"] in existing_pmids:
            continue

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
        )
        session.add(row)
        new_count += 1

    if is_initial:
        sub.initial_poll_done = True

    session.commit()
    return new_count


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
        logger.warning("Gmail 未配置，跳过发送 (Gmail not configured, skipping send) for subscription %s", sub.id)
        return

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
    """
    session = get_session()
    try:
        settings = get_settings(session)
        now = dt.datetime.utcnow()
        subs = session.query(Subscription).filter(Subscription.active.is_(True)).all()
        for sub in subs:
            if not is_due(sub, now):
                continue
            n = poll_subscription(session, sub, settings)
            if n:
                logger.info("订阅 %s 发现 %d 篇新文献 (found %d new articles)", sub.label, n, n)
            dispatch_subscription(session, sub, settings)
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
    _scheduler.start()
    return _scheduler
