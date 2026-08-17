#!/usr/bin/env bash
# 在 macOS 上把 PubMed Alert 打包成一个独立的 .app，运行的人不需要装 Python，双击图标即可用，
# 不会弹出终端窗口。
# Packages PubMed Alert into a standalone .app on macOS — no Python needed to run it, double-click
# the icon like any normal Mac app, no terminal window pops up.
#
# 必须在真正的 Mac 上运行这个脚本 —— PyInstaller 不能跨平台编译（不能在 Windows 上生成 Mac 的包）。
# Must be run on an actual Mac — PyInstaller cannot cross-compile between operating systems.
#
# 用法 Usage:
#   chmod +x packaging/build_mac.sh
#   ./packaging/build_mac.sh
#
# 打包结果在 dist/mac/PubMedAlert.app，同目录下还会生成一个 PubMedAlert.zip，直接把这个 zip
# 发给对方即可（压缩包能完整保留 .app 的内部结构，用文件直传或网盘分享都不会损坏）。
# Output: dist/mac/PubMedAlert.app, plus a PubMedAlert.zip alongside it — send that zip file to
# recipients (zipping preserves the .app bundle's internal structure intact across file transfer
# or cloud-drive sharing).

set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt pyinstaller

./.venv/bin/pyinstaller --noconfirm --windowed --name PubMedAlert \
    --distpath dist/mac \
    --workpath build/mac \
    --add-data "app/templates:app/templates" \
    --add-data "app/static:app/static" \
    --copy-metadata APScheduler \
    --collect-submodules uvicorn \
    run.py

# 自签名（ad-hoc）：不是正式的 Apple 开发者签名，但能避免 Apple Silicon 上常见的
# "PubMedAlert 已损坏，无法打开" 报错（这个报错和下面的 Gatekeeper 提示是两回事，
# 不自签名的话即使右键「打开」也会遇到）。
# Ad-hoc self-signing: not a real Apple Developer signature, but it avoids the "PubMedAlert is
# damaged and can't be opened" error that's common on Apple Silicon for unsigned apps (this is a
# different error from the Gatekeeper prompt below — without this, even right-click-Open hits it).
codesign --force --deep --sign - "dist/mac/PubMedAlert.app"

(cd dist/mac && rm -f PubMedAlert.zip && ditto -c -k --keepParent PubMedAlert.app PubMedAlert.zip)

echo ""
echo "完成 Done: dist/mac/PubMedAlert.app (发这个压缩包 send this zip: dist/mac/PubMedAlert.zip)"
echo ""
echo "注意 / Note: macOS Gatekeeper 会拦截未签名的 App。接收者解压后，第一次运行不能直接"
echo "双击，需要在「访达 Finder」里右键点 PubMedAlert.app -> 选「打开 Open」，在弹出的安全"
echo "提示里再次确认「打开」。之后就可以正常双击了，不会再弹终端窗口。"
echo "Recipients: after unzipping, the first run must NOT be a plain double-click — right-click"
echo "PubMedAlert.app in Finder, choose \"Open\", then confirm \"Open\" again in the Gatekeeper"
echo "prompt. After that, double-clicking works normally — no terminal window appears."
