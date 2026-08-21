import json
import datetime as dt

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, Text, Float,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from app.config import DATABASE_URL
from app import crypto

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

FREQUENCY_CHOICES = ["immediate", "daily", "every_3_days", "weekly"]


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)  # 唯一索引在迁移里建，见 _migrate_add_missing_columns
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class PendingRegistration(Base):
    """还没验证邮箱的注册请求；验证码对了才会真正变成一条 User。
    A registration that hasn't verified its email yet; only becomes a real User once the code
    checks out.
    """
    __tablename__ = "pending_registrations"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    username = Column(String(50), nullable=False)
    password_hash = Column(String(255), nullable=False)
    code_hash = Column(String(64), nullable=False)
    attempts = Column(Integer, default=0)
    last_sent_at = Column(DateTime, default=dt.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class PasswordReset(Base):
    """找回密码用的验证码请求。Password-reset verification code request."""
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code_hash = Column(String(64), nullable=False)
    attempts = Column(Integer, default=0)
    last_sent_at = Column(DateTime, default=dt.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class Session(Base):
    """登录会话；cookie 里放的是原始随机 token，这里只存它的哈希，防止数据库泄露直接可用。
    Login session; the cookie holds the raw random token — only its hash is stored here, so a
    DB leak doesn't directly hand out usable login sessions.
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    label = Column(String(200), nullable=False)

    keywords_json = Column(Text, default="[]")   # JSON list of str
    journals_json = Column(Text, default="[]")   # JSON list of str
    authors_json = Column(Text, default="[]")    # JSON list of str
    query_override = Column(Text, nullable=True)  # 用户直接编辑的 PubMed 检索式（优先生效）

    recipient_email = Column(String(255), nullable=False)
    frequency = Column(String(20), default="immediate")  # see FREQUENCY_CHOICES
    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    last_dispatched_at = Column(DateTime, nullable=True)
    # 是否已经完成过"首次轮询"（首次发送近5年内最相关的10篇，此后改为只发最新更新）
    # whether the "first poll" has already run (sends the 10 most relevant articles from the
    # last 5 years; afterwards, switches to sending only newly-updated articles)
    initial_poll_done = Column(Boolean, default=False)

    articles = relationship("SeenArticle", back_populates="subscription", cascade="all, delete-orphan")

    @property
    def keywords(self):
        return json.loads(self.keywords_json or "[]")

    @keywords.setter
    def keywords(self, value):
        self.keywords_json = json.dumps(value, ensure_ascii=False)

    @property
    def journals(self):
        return json.loads(self.journals_json or "[]")

    @journals.setter
    def journals(self, value):
        self.journals_json = json.dumps(value, ensure_ascii=False)

    @property
    def authors(self):
        return json.loads(self.authors_json or "[]")

    @authors.setter
    def authors(self, value):
        self.authors_json = json.dumps(value, ensure_ascii=False)


class SeenArticle(Base):
    __tablename__ = "seen_articles"
    __table_args__ = (UniqueConstraint("subscription_id", "pmid", name="uq_subscription_pmid"),)

    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)

    pmid = Column(String(20), nullable=False)
    title = Column(Text)
    authors = Column(Text)
    journal = Column(String(500))
    pub_date = Column(String(50))
    doi = Column(String(200), nullable=True)
    abstract = Column(Text, nullable=True)

    jcr_quartile = Column(String(10), nullable=True)   # 官方 JCR 分区，例如 "Q1" official JCR quartile, e.g. "Q1"
    jif = Column(Float, nullable=True)                  # 影响因子 (Journal Impact Factor)

    # 首次检索"相关+最新"双批次的标记（互不排斥，一篇文章可能两个都是 True）；后续增量发现的
    # 文章两个都是 False。Flags for the initial "relevant + recent" dual-batch search (not
    # mutually exclusive — an article can be in both); regular incremental finds have both False.
    initial_relevant = Column(Boolean, default=False)
    initial_recent = Column(Boolean, default=False)

    # 待阅读清单。Reading list.
    saved_for_reading = Column(Boolean, default=False)
    saved_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    # 用户自己打的星级，表示阅读优先级；0 = 未打分。
    # User-assigned star rating indicating reading priority; 0 = unrated.
    priority = Column(Integer, default=0)

    # 开放获取全文 PDF 链接（首次发现这篇文章时查一次 Unpaywall，查不到就是 None，不会重试）。
    # Open-access full-text PDF link (looked up once via Unpaywall when the article is first
    # found; None if no OA copy was found — never retried afterward).
    oa_pdf_url = Column(String(500), nullable=True)

    first_seen_at = Column(DateTime, default=dt.datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

    subscription = relationship("Subscription", back_populates="articles")

    @property
    def pubmed_url(self):
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"


class AppSettings(Base):
    """每个用户各自的设置（发件邮箱等），通过网页「设置」页面编辑。
    Per-user settings (sender email, etc.), edited via the web "Settings" page.
    """
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    smtp_host = Column(String(255), default="smtp.gmail.com")
    smtp_port = Column(Integer, default=587)
    smtp_use_ssl = Column(Boolean, default=False)  # True=隐式SSL(常见465端口) False=STARTTLS(常见587端口)
    sender_email = Column(String(255), default="")
    sender_password_enc = Column(String(500), default="")
    ncbi_api_key = Column(String(200), default="")
    poll_interval_hours = Column(Float, default=6.0)
    ui_language = Column(String(10), default="zh")  # 默认界面语言 default UI language

    @property
    def sender_password(self):
        return crypto.decrypt(self.sender_password_enc)

    @sender_password.setter
    def sender_password(self, value):
        self.sender_password_enc = crypto.encrypt(value)


def _migrate_add_missing_columns():
    """给已存在的旧数据库补上新增列（轻量迁移，SQLite 专用）。
    Add newly-introduced columns to an already-existing DB (lightweight, SQLite-only migration).
    """
    with engine.connect() as conn:
        cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(subscriptions)")]
        if "initial_poll_done" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE subscriptions ADD COLUMN initial_poll_done BOOLEAN DEFAULT 0"
            )
            # 已经有过文献记录的旧订阅，视为已经完成过首次轮询
            # subscriptions that already have article history are treated as past their first poll
            conn.exec_driver_sql(
                "UPDATE subscriptions SET initial_poll_done = 1 "
                "WHERE id IN (SELECT DISTINCT subscription_id FROM seen_articles)"
            )
            conn.commit()

        article_cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(seen_articles)")]
        if "jcr_quartile" not in article_cols:
            conn.exec_driver_sql("ALTER TABLE seen_articles ADD COLUMN jcr_quartile VARCHAR(10)")
        if "jif" not in article_cols:
            conn.exec_driver_sql("ALTER TABLE seen_articles ADD COLUMN jif FLOAT")
        if "initial_relevant" not in article_cols:
            conn.exec_driver_sql("ALTER TABLE seen_articles ADD COLUMN initial_relevant BOOLEAN DEFAULT 0")
        if "initial_recent" not in article_cols:
            conn.exec_driver_sql("ALTER TABLE seen_articles ADD COLUMN initial_recent BOOLEAN DEFAULT 0")
        if "saved_for_reading" not in article_cols:
            conn.exec_driver_sql("ALTER TABLE seen_articles ADD COLUMN saved_for_reading BOOLEAN DEFAULT 0")
        if "saved_at" not in article_cols:
            conn.exec_driver_sql("ALTER TABLE seen_articles ADD COLUMN saved_at DATETIME")
        if "read_at" not in article_cols:
            conn.exec_driver_sql("ALTER TABLE seen_articles ADD COLUMN read_at DATETIME")
        if "priority" not in article_cols:
            conn.exec_driver_sql("ALTER TABLE seen_articles ADD COLUMN priority INTEGER DEFAULT 0")
        if "oa_pdf_url" not in article_cols:
            conn.exec_driver_sql("ALTER TABLE seen_articles ADD COLUMN oa_pdf_url VARCHAR(500)")
        conn.commit()

        # 旧版本只支持 Gmail，字段叫 gmail_address / gmail_app_password_enc；这里迁移到通用的
        # SMTP 字段（sender_email / sender_password_enc / smtp_host / smtp_port / smtp_use_ssl）。
        # Older versions only supported Gmail, with columns named gmail_address /
        # gmail_app_password_enc; migrate them to the generic SMTP columns here.
        settings_cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(app_settings)")]
        if "gmail_address" in settings_cols and "sender_email" not in settings_cols:
            conn.exec_driver_sql("ALTER TABLE app_settings ADD COLUMN sender_email VARCHAR(255) DEFAULT ''")
            conn.exec_driver_sql("ALTER TABLE app_settings ADD COLUMN sender_password_enc VARCHAR(500) DEFAULT ''")
            conn.exec_driver_sql("ALTER TABLE app_settings ADD COLUMN smtp_host VARCHAR(255) DEFAULT 'smtp.gmail.com'")
            conn.exec_driver_sql("ALTER TABLE app_settings ADD COLUMN smtp_port INTEGER DEFAULT 587")
            conn.exec_driver_sql("ALTER TABLE app_settings ADD COLUMN smtp_use_ssl BOOLEAN DEFAULT 0")
            conn.exec_driver_sql(
                "UPDATE app_settings SET sender_email = gmail_address, "
                "sender_password_enc = gmail_app_password_enc, "
                "smtp_host = 'smtp.gmail.com', smtp_port = 587, smtp_use_ssl = 0"
            )
            conn.exec_driver_sql("ALTER TABLE app_settings DROP COLUMN gmail_address")
            conn.exec_driver_sql("ALTER TABLE app_settings DROP COLUMN gmail_app_password_enc")
            conn.commit()

        # 引入多用户登录：给订阅和设置各加一个"归属用户"列。旧数据库里已有的行没有归属，
        # 会在第一个用户注册时被自动认领（见 main.py 的 /register 处理逻辑）。
        # Introducing multi-user login: add an "owning user" column to subscriptions and
        # settings. Pre-existing rows in an older database have no owner yet — they get
        # auto-adopted by whichever user registers first (see the /register handler in main.py).
        sub_cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(subscriptions)")]
        if "user_id" not in sub_cols:
            conn.exec_driver_sql("ALTER TABLE subscriptions ADD COLUMN user_id INTEGER REFERENCES users(id)")
            conn.commit()

        settings_cols2 = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(app_settings)")]
        if "user_id" not in settings_cols2:
            conn.exec_driver_sql("ALTER TABLE app_settings ADD COLUMN user_id INTEGER REFERENCES users(id)")
            conn.commit()

        # 加用户名登录：SQLite 的 ADD COLUMN 不支持直接带 UNIQUE/NOT NULL，所以分三步——先加个
        # 不带约束的列，用 Python 给已有账号回填一个占位用户名（避免和已有账号数量对不上导致的
        # 唯一性冲突），最后才建唯一索引。
        # Adding username-based login: SQLite's ADD COLUMN can't carry UNIQUE/NOT NULL directly,
        # so this happens in three steps — add an unconstrained column, backfill a placeholder
        # username in Python for any pre-existing accounts, then create the unique index last.
        user_cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)")]
        if "username" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN username VARCHAR(50)")
            conn.commit()
            for row in conn.exec_driver_sql("SELECT id, email FROM users WHERE username IS NULL"):
                placeholder = f"{row[1].split('@')[0]}_{row[0]}"
                conn.exec_driver_sql(
                    "UPDATE users SET username = ? WHERE id = ?", (placeholder, row[0])
                )
            conn.commit()
            conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username ON users(username)")
            conn.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_add_missing_columns()


def get_session():
    return SessionLocal()


def get_db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()
