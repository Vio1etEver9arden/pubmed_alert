# Changelog

This file documents notable changes to this project. Format follows
[Keep a Changelog](https://keepachangelog.com/), version numbers follow
[Semantic Versioning](https://semver.org/).

本文件记录本项目每个版本的重要变化。格式参照 [Keep a Changelog](https://keepachangelog.com/)，版本号规则参照 [语义化版本 SemVer](https://semver.org/lang/zh-CN/)。

## [1.1.1] - 2026-08-17

### Added
- Generic SMTP sending: pick your provider (Gmail / QQ Mail / 163 Mail / Outlook) from a dropdown on the Settings page and the SMTP host/port/SSL are filled in automatically, or choose "Custom" to enter any other provider's SMTP server by hand.
  发件邮箱改为通用 SMTP：在「设置」页面下拉选择邮箱服务商（Gmail / QQ邮箱 / 163邮箱 / Outlook），SMTP 服务器/端口/SSL 会自动填好；也可以选「自定义」手动填写其他任意邮箱服务商的 SMTP 信息。

- macOS packaging now produces a proper `.app` bundle (`--windowed` mode) instead of a bare executable — double-clicking no longer opens a terminal window, and the build script applies a local ad-hoc code signature to avoid the "app is damaged" error on Apple Silicon.
  macOS 打包改为生成正规的 `.app`（`--windowed` 模式），双击不再弹出终端窗口；构建脚本还会做本机自签名，避免 Apple Silicon 上「应用已损坏」的报错。
- Launching the app while an instance is already running no longer errors out — it just opens the browser to the existing instance instead of trying to bind the port again.
  在已有实例运行时再次启动程序不会再报错——会直接把浏览器打开到现有实例，而不是尝试重新占用端口。

### Changed
- Existing Gmail credentials are migrated automatically to the new generic settings on first startup after upgrading — no action needed.
  升级后首次启动会自动把已有的 Gmail 配置迁移到新的通用设置字段，无需手动操作。

## [1.0.0] - 2026-08-17

### Added
- Subscribe to new PubMed literature by keyword / journal / author, with instant or periodic summary email delivery.
  按关键词 / 期刊 / 作者订阅 PubMed 新文献，支持即时或按周期汇总发送邮件。
- Emails are annotated with official JCR impact factor and quartile (obtained by locally parsing your own exported JCR PDF, see `scripts/parse_jcr_pdf.py`).
  邮件中标注官方 JCR 影响因子和分区（通过本地解析自己导出的 JCR PDF 获得，见 `scripts/parse_jcr_pdf.py`）。
- Web interface for managing subscriptions, supporting Chinese / English / Japanese.
  网页界面管理订阅，支持中文 / English / 日本語。
- Sends via Gmail, with the password stored encrypted.
  通过 Gmail 发信，密码加密存储。
- Standalone packaging support for Windows / macOS (PyInstaller), for sharing with people who don't use Python.
  Windows / macOS 独立打包支持（PyInstaller），方便分享给不用 Python 的人。
