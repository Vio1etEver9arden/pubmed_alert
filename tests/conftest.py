"""
pytest 的公共设置文件——pytest 会在收集测试之前自动先运行这个文件。
最关键的一件事：在任何 `app.xxx` 模块被 import 之前，先把 PUBMED_ALERT_DATA_DIR 和
REGISTER_INVITE_CODE 这两个环境变量设置好，让程序以为自己的"数据目录"是一个临时文件夹，
而不是真实项目里的 data/ 文件夹——这样测试永远不会碰到真实的 data/subscriptions.db。

pytest's shared setup file — pytest automatically runs this before collecting any tests.
The one thing that matters most: set the PUBMED_ALERT_DATA_DIR and REGISTER_INVITE_CODE
environment variables BEFORE any `app.xxx` module gets imported, so the app thinks its "data
directory" is a temp folder instead of the real project's data/ folder — meaning tests can never
touch the real data/subscriptions.db.
"""
import os
import tempfile

_TEST_DATA_DIR = tempfile.mkdtemp(prefix="pubmed_alert_test_")
os.environ["PUBMED_ALERT_DATA_DIR"] = _TEST_DATA_DIR
os.environ["REGISTER_INVITE_CODE"] = "test-invite-code"

# 上面两行必须在这些 import 之前执行，因为 app/config.py 是"一 import 就把路径算好"的写法。
# The two lines above must run before these imports, since app/config.py computes its paths as
# soon as it's imported.
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine, get_session  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def no_real_emails(monkeypatch):
    """把"真的发邮件"这几个函数换成什么都不做的假函数，每个测试都会自动套用。

    之前这里漏了这一步：测试注册账号时会真的调用发验证码邮件的代码，而那段代码用的是
    .env 里配置的真实 Gmail 账号——也就是说跑测试会真的往外发邮件。这个 fixture 用
    monkeypatch 把 app.mailer 里三个"真的发邮件"的函数替换成空函数，跑完测试后
    monkeypatch 会自动把原来的函数换回来，不影响正常运行的程序。

    Replaces the real "send an email" functions with do-nothing fakes, applied automatically
    to every test (autouse=True).

    This was missing before: registering an account in a test would really call the
    verification-email code, which uses the real Gmail account configured in .env — so running
    tests actually sent outbound email. This fixture uses monkeypatch to swap out the three
    real-sending functions in app.mailer for no-ops; monkeypatch automatically restores the
    originals after each test, so the real running app is unaffected.
    """
    import app.mailer as mailer

    monkeypatch.setattr(mailer, "send_verification_email", lambda *a, **k: None)
    monkeypatch.setattr(mailer, "send_digest", lambda *a, **k: None)
    monkeypatch.setattr(mailer, "send_test_email", lambda *a, **k: None)


@pytest.fixture(autouse=True)
def fresh_database():
    """每个测试函数跑之前，都重新建一份空白表；跑完再清空。
    确保测试之间互不干扰——这个测试建的账号，不会被下一个测试看到。
    Before every test function, (re)create a clean set of empty tables; wipe them again
    afterward. Keeps tests from interfering with each other — an account created by one test
    is never visible to the next.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """给测试直接用的数据库会话，跟网页请求内部用的是同一个函数。
    A database session for tests to use directly — the same function the web routes use
    internally.
    """
    session = get_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """模拟浏览器发请求，但不用真的起一个网络服务器、不会跟真实的 8000 端口冲突。
    Simulates a browser making requests, without actually starting a real network server or
    colliding with the real port 8000.
    """
    return TestClient(app)


def register_and_login(client: TestClient, db_session, username: str, email: str,
                        password: str = "testpass123") -> None:
    """帮测试快速注册并登录一个账号：走完注册两步验证的流程，之后 client 上的 cookie 就带着
    登录状态了，后面的请求都会被当成这个用户。

    这里没有真的去读邮箱验证码（测试环境也没有真的发邮件），而是直接把数据库里那条"待验证"记录
    的验证码改成一个测试里知道的值——这是"抄近路"，但因为我们自己就是在测数据库，这么做是安全
    透明的，不是作弊。

    Registers and logs in an account for tests: walks through the two-step verification flow, so
    afterward the client's cookies carry a logged-in session — subsequent requests are treated as
    this user.

    This doesn't actually read a verification code from an inbox (no real email is sent in
    tests) — instead it directly overwrites the pending registration's code with a value the test
    already knows. That's a shortcut, but a safe and transparent one, since we're the ones
    inspecting the database directly.
    """
    from app.auth import hash_code
    from app.db import PendingRegistration

    client.post("/register", data={
        "username": username, "email": email,
        "password": password, "password_confirm": password,
        "invite_code": "test-invite-code",
    })
    pending = db_session.query(PendingRegistration).filter_by(email=email).first()
    pending.code_hash = hash_code("111111")
    db_session.commit()
    client.post("/register/verify", data={"email": email, "code": "111111"})
