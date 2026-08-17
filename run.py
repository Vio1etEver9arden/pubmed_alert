"""启动入口 / Entry point: python run.py（打包成 exe 后双击运行，会自动打开浏览器）
Entry point: python run.py (when packaged as an exe, double-click it — the browser opens automatically)
"""
import socket
import threading
import time
import webbrowser

import uvicorn

from app.main import app

HOST = "127.0.0.1"
PORT = 8000


def _open_browser(delay=1.5):
    time.sleep(delay)
    webbrowser.open(f"http://{HOST}:{PORT}")


def _already_running() -> bool:
    """程序已经在后台跑着（比如上次没退出）时返回 True。
    True if an instance is already listening on our port (e.g. left running from last time).

    这个服务本来就该一直在后台跑，不依赖浏览器开着（这样订阅到期才能按时检查发信）；用户可能会
    重复双击图标，这时不该报错或起第二份，而是直接把浏览器带到已经在跑的那个上面。
    This service is meant to keep running in the background regardless of whether a browser tab
    is open (so due subscriptions still get checked and sent on schedule). Users may double-click
    the icon again while it's already running — in that case we shouldn't error out or start a
    second instance, just point the browser at the one that's already up.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, PORT)) == 0


if __name__ == "__main__":
    if _already_running():
        _open_browser(delay=0)
    else:
        threading.Thread(target=_open_browser, daemon=True).start()
        uvicorn.run(app, host=HOST, port=PORT, reload=False)
