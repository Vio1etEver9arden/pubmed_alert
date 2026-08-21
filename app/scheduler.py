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
from concurrent.futures import ThreadPoolExecutor

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app import mailer, pubmed, journal_rank, unpaywall, ai
from app.db import get_session, Subscription, SeenArticle, PendingRegistration, PasswordReset
from app.settings import get_settings

logger = logging.getLogger("pubmed_alert.scheduler")

TICK_JOB_ID = "check_due_subscriptions"
TICK_MINUTES = 15  # 心跳粒度，不需要用户配置 heartbeat granularity, not user-configurable

CLEANUP_JOB_ID = "cleanup_expired_auth_rows"
CLEANUP_MINUTES = 60

TREND_JOB_ID = "send_trend_digests"
TREND_WINDOW_DAYS = 30  # 趋势总结抓取"最近多少天"的文章 how many trailing days the trend digest gathers
TREND_MIN_INTERVAL = dt.timedelta(days=27)  # 留点余量,防止某次 cron 因程序重启没跑到而被拖过一整月

MAX_ENRICHMENT_WORKERS = 8  # Unpaywall/AI 并发查询的线程数上限 concurrency cap for Unpaywall/AI lookups

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


def is_trend_due(sub: Subscription, now: dt.datetime) -> bool:
    """判断某个订阅现在是否该发"月度趋势总结"了。从没发过就是到期；发过的话要满
    TREND_MIN_INTERVAL（27天，比一个月略短，防止某次 cron 因为程序重启没跑到，被拖过一整月）。
    Whether a subscription is due for its "monthly trend digest". Never sent before means due;
    otherwise due once TREND_MIN_INTERVAL (27 days — slightly under a month, so a missed cron
    firing from a restart doesn't push it out a full extra month) has passed.
    """
    if sub.last_trend_sent_at is None:
        return True
    return (now - sub.last_trend_sent_at) >= TREND_MIN_INTERVAL


def _subscription_topic(sub: Subscription) -> str:
    parts = [sub.label]
    if sub.keywords:
        parts.append("keywords: " + ", ".join(sub.keywords))
    return " | ".join(parts)


def _fetch_enrichment(art: dict, sub: Subscription, settings, langs):
    """在线程池的工作线程里跑：查 Unpaywall 全文链接 + 生成 AI 内容，两个都是慢的网络调用。
    只读数据（art/sub 的属性、settings），不碰数据库会话，所以可以安全地多线程并发跑。
    Runs inside a thread-pool worker: looks up the Unpaywall full-text link and generates AI
    content — both slow network calls. Only reads data (art/sub attributes, settings), never
    touches the database session, so it's safe to run concurrently across threads.
    """
    oa_pdf_url = unpaywall.lookup(art["doi"])
    enrichment = ai.enrich_article(art, _subscription_topic(sub), langs, settings) or {}
    return oa_pdf_url, enrichment


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

    new_articles = []
    seen_this_batch = set()  # 防止两批检索有重叠时，同一个 pmid 被插入两次
    for art in articles:
        if art["pmid"] in existing_pmids or art["pmid"] in seen_this_batch:
            continue
        seen_this_batch.add(art["pmid"])
        new_articles.append(art)

    # Unpaywall 查询、AI 生成内容都是"等网络"的慢操作，用线程池并发跑，不再一篇一篇排队等——
    # 一次发现几十篇新文章时（比如新订阅首次检索），总耗时能从"篇数 x 单篇耗时"降到接近单篇耗时。
    # 数据库写入（session.add）不是线程安全的，所以并发只发生在这一步，实际建行、入库还是留在
    # 主线程里顺序执行。
    # Unpaywall lookups and AI generation are both slow "wait on the network" operations, run
    # concurrently in a thread pool instead of one-at-a-time — discovering dozens of new articles
    # at once (e.g. a new subscription's first poll) drops total wait time from roughly
    # "count × per-article time" down to close to one per-article time. Database writes
    # (session.add) aren't thread-safe, so concurrency is scoped to this step only — building rows
    # and inserting them stays sequential, back on the main thread.
    langs = mailer.target_langs(settings.ui_language)
    enrichment_by_pmid = {}
    if new_articles:
        with ThreadPoolExecutor(max_workers=min(MAX_ENRICHMENT_WORKERS, len(new_articles))) as pool:
            futures = {
                pool.submit(_fetch_enrichment, art, sub, settings, langs): art["pmid"]
                for art in new_articles
            }
            for future in futures:
                pmid = futures[future]
                enrichment_by_pmid[pmid] = future.result()

    new_count = 0
    for art in new_articles:
        rank = journal_rank.lookup(
            journal_title=art["journal"],
            issn=art.get("issn"),
            issn_linking=art.get("issn_linking"),
        )
        oa_pdf_url, enrichment = enrichment_by_pmid[art["pmid"]]

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
            oa_pdf_url=oa_pdf_url,
            ai_summary_en=enrichment.get("summary_en"),
            ai_summary_local=enrichment.get("summary_local"),
            ai_relevance_score=enrichment.get("relevance_score"),
            ai_translated_title=enrichment.get("translated_title"),
        )
        if enrichment.get("keywords"):
            row.ai_keywords = enrichment["keywords"]
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

    # 按 AI 相关性打分从高到低排序，让相关性高的文章排在邮件前面（也因此更可能落在
    # EMAIL_MAX_ARTICLES 那个"完整展示"的上限之内，见 app/mailer.py）；没打分的文章（没配置
    # AI，或者是配置 AI 之前就发现的老文章）分数是 NULL，SQL 排序里 NULL 天然排在最后，会
    # 自动按 first_seen_at 退回到原来的"先发现先发送"顺序——不需要额外判断"配没配置 AI"。
    # Sorted by AI relevance score, highest first, so more relevant articles appear earlier in
    # the email (and are therefore more likely to fall within EMAIL_MAX_ARTICLES's "fully shown"
    # cap — see app/mailer.py). Unscored articles (AI not configured, or discovered before AI was
    # enabled) have a NULL score, which SQL orders last by default, so they naturally fall back to
    # the original first-discovered-first-sent order — no separate "is AI configured" branch needed.
    pending = (
        session.query(SeenArticle)
        .filter(SeenArticle.subscription_id == sub.id, SeenArticle.sent_at.is_(None))
        .order_by(SeenArticle.ai_relevance_score.desc(), SeenArticle.first_seen_at.asc())
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


def _article_dict(a: SeenArticle) -> dict:
    return {
        "title": a.title, "abstract": a.abstract, "pmid": a.pmid,
        "ai_summary_en": a.ai_summary_en,
    }


def _send_trend_digest_for_subscription(session, sub: Subscription, settings, now: dt.datetime):
    window_start = now - dt.timedelta(days=TREND_WINDOW_DAYS)
    articles = (
        session.query(SeenArticle)
        .filter(SeenArticle.subscription_id == sub.id, SeenArticle.first_seen_at >= window_start)
        .order_by(SeenArticle.first_seen_at.asc())
        .all()
    )
    if not articles:
        return  # 这个月没有新文章，跳过，不动 last_trend_sent_at no new articles this month, skip

    langs = mailer.target_langs(settings.ui_language)
    prose = ai.write_trend_digest(sub.label, [_article_dict(a) for a in articles], langs, settings)
    if prose is None:
        return  # AI 调用失败，下个月再试，不发一封没有内容的邮件

    try:
        mailer.send_trend_digest(settings, sub, articles, prose)
    except Exception:
        logger.exception("发送月度趋势总结失败 (trend digest send failed) for subscription %s", sub.id)
        return

    sub.last_trend_sent_at = now
    session.commit()


def send_trend_digests():
    """每月一次的"趋势总结"邮件——只对配置了 AI 的用户名下、到期的订阅生效，没配置 AI 的用户
    静默跳过（不算错误）。
    The once-a-month "trend digest" email — only for subscriptions belonging to users who've
    configured AI; users without AI configured are silently skipped (not an error).
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
            if not is_trend_due(sub, now):
                continue
            settings = settings_cache.get(sub.user_id)
            if settings is None:
                settings = get_settings(session, sub.user_id)
                settings_cache[sub.user_id] = settings
            if not ai.is_configured(settings):
                continue
            _send_trend_digest_for_subscription(session, sub, settings, now)
    finally:
        session.close()


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
    _scheduler.add_job(
        send_trend_digests,
        trigger=CronTrigger(day=1, hour=8),
        # 故意不给 next_run_time——"每月一次"的任务不应该在每次程序重启时也跟着多跑一次。
        # Deliberately no next_run_time — a "once a month" job shouldn't also fire on every
        # process restart.
        id=TREND_JOB_ID,
        max_instances=1,
    )
    _scheduler.start()
    return _scheduler
