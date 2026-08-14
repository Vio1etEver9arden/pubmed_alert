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


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
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

    sjr_quartile = Column(String(10), nullable=True)   # e.g. "Q1"
    sjr_rank = Column(Integer, nullable=True)           # SJR 排名（在该分类下）

    first_seen_at = Column(DateTime, default=dt.datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

    subscription = relationship("Subscription", back_populates="articles")

    @property
    def pubmed_url(self):
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"


class AppSettings(Base):
    """全局设置，单例（固定 id=1），通过网页「设置」页面编辑。
    Global settings, a singleton row (fixed id=1), edited via the web "Settings" page.
    """
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True)
    gmail_address = Column(String(255), default="")
    gmail_app_password_enc = Column(String(500), default="")
    ncbi_api_key = Column(String(200), default="")
    poll_interval_hours = Column(Float, default=6.0)
    ui_language = Column(String(10), default="zh")  # 默认界面语言 default UI language

    @property
    def gmail_app_password(self):
        return crypto.decrypt(self.gmail_app_password_enc)

    @gmail_app_password.setter
    def gmail_app_password(self, value):
        self.gmail_app_password_enc = crypto.encrypt(value)


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


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_add_missing_columns()


def get_session():
    return SessionLocal()
