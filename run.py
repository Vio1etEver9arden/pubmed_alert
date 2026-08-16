"""启动入口 / Entry point: python run.py（打包成 exe 后双击运行，会自动打开浏览器）
Entry point: python run.py (when packaged as an exe, double-click it — the browser opens automatically)
"""
import threading
import time
import webbrowser

import uvicorn

from app.main import app

HOST = "127.0.0.1"
PORT = 8000


def _open_browser():
    time.sleep(1.5)
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(app, host=HOST, port=PORT, reload=False)
