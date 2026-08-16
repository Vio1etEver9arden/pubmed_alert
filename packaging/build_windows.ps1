# 在 Windows 上把 PubMed Alert 打包成一个独立的 PubMedAlert.exe，运行的人不需要装 Python。
# Packages PubMed Alert into a standalone PubMedAlert.exe on Windows — no Python needed to run it.
#
# 用法 Usage:
#   powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
#
# 打包结果在 dist\windows\PubMedAlert.exe。把这一个文件发给别人，建议对方先放进一个新建的空
# 文件夹里再双击运行（会在旁边生成 data\ 文件夹存数据库和密钥，不要放进 Program Files 之类没
# 有写权限的目录）。
# Output: dist\windows\PubMedAlert.exe. Send just this one file — have recipients put it in a new
# empty folder before double-clicking (a data\ folder appears next to it for the DB and secret
# key; avoid read-only locations like Program Files).

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller

& ".venv\Scripts\pyinstaller.exe" --noconfirm --onefile --name PubMedAlert `
    --distpath dist/windows `
    --workpath build/windows `
    --add-data "app/templates;app/templates" `
    --add-data "app/static;app/static" `
    --copy-metadata APScheduler `
    --collect-submodules uvicorn `
    run.py

Write-Host ""
Write-Host "完成 Done: dist\windows\PubMedAlert.exe"
