#!/usr/bin/env bash
# 在 macOS 上把 PubMed Alert 打包成一个独立的可执行文件，运行的人不需要装 Python。
# Packages PubMed Alert into a standalone executable on macOS — no Python needed to run it.
#
# 必须在真正的 Mac 上运行这个脚本 —— PyInstaller 不能跨平台编译（不能在 Windows 上生成 Mac 的包）。
# Must be run on an actual Mac — PyInstaller cannot cross-compile between operating systems.
#
# 用法 Usage:
#   chmod +x packaging/build_mac.sh
#   ./packaging/build_mac.sh
#
# 打包结果在 dist/mac/PubMedAlert。
# Output: dist/mac/PubMedAlert

set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt pyinstaller

./.venv/bin/pyinstaller --noconfirm --onefile --name PubMedAlert \
    --distpath dist/mac \
    --workpath build/mac \
    --add-data "app/templates:app/templates" \
    --add-data "app/static:app/static" \
    --copy-metadata APScheduler \
    --collect-submodules uvicorn \
    run.py

echo ""
echo "完成 Done: dist/mac/PubMedAlert"
echo ""
echo "注意 / Note: macOS Gatekeeper 会拦截未签名的可执行文件。接收者拿到文件后，第一次"
echo "运行不能直接双击，需要在「访达 Finder」里右键点它 -> 选「打开 Open」，在弹出的安全"
echo "提示里再次确认「打开」。之后就可以正常双击了。"
echo "Recipients: the first run must NOT be a plain double-click — right-click the file in"
echo "Finder, choose \"Open\", then confirm \"Open\" again in the Gatekeeper security prompt."
echo "After that, double-clicking works normally."
