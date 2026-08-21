# Changelog

This file documents notable changes to this project. Format follows
[Keep a Changelog](https://keepachangelog.com/), version numbers follow
[Semantic Versioning](https://semver.org/).

本文件记录本项目每个版本的重要变化。格式参照 [Keep a Changelog](https://keepachangelog.com/)，版本号规则参照 [语义化版本 SemVer](https://semver.org/lang/zh-CN/)。

## [1.2.1] - 2026-08-21

### Added
- Export any subscription's articles or your whole reading list as an RIS citation file, compatible with EndNote / Zotero / Mendeley.
  可以把某个订阅的文献或整个待阅读清单导出为 RIS 格式引文文件，兼容 EndNote / Zotero / Mendeley。
- Keywords/journals/authors now also accept commas, Chinese enumeration commas (、), and semicolons as separators, in addition to one-per-line.
  关键词/期刊/作者除了换行分隔，现在也支持用英文逗号、中文逗号、顿号、分号分隔。
- A search box on the article list and reading list pages, matching against title / journal / authors.
  文献列表和待阅读清单页面新增搜索框，可按标题/期刊/作者搜索。
- A "Export my data (backup)" button on the Settings page, downloading all your subscriptions and discovered articles as one JSON file.
  「设置」页面新增"导出我的数据（备份）"按钮，把所有订阅和已发现文献导出成一份 JSON 文件。
- A 1–5 star reading-priority rating on saved articles.
  文献可以打 1–5 星表示阅读优先级。
- Open-access full-text PDF links, looked up automatically via [Unpaywall](https://unpaywall.org/) the first time an article is found, and shown on the web pages and in alert emails when available.
  新增开放获取全文 PDF 链接——首次发现文章时自动通过 [Unpaywall](https://unpaywall.org/) 查询一次，查得到的话会在网页和邮件里显示。
- A note on the web and in alert emails when the same article matches more than one of your subscriptions — both emails still get sent, just annotated, so it's clear it isn't a duplicate mistake.
  同一篇文章同时命中你名下多个订阅时，网页和邮件里都会标注一下——两边邮件仍然照常发送，只是加一句提示，避免误以为是重复发错了。
- A first automated test suite (pytest), covering password/token/invite-code logic, IDOR/ownership regression checks, RIS formatting, and keyword parsing, running against a fully isolated temporary database and with all outbound email mocked out.
  新增第一批自动化测试（pytest），覆盖密码/令牌/邀请码逻辑、权限隔离（IDOR）回归检查、RIS 格式、关键词拆分，全程用隔离的临时数据库、发邮件也全部打桩，不会碰真实数据或真的发邮件。

## [1.2.0] - 2026-08-19

### Added
- Multi-user login: anyone can register an account (email + password + invite code); each account only sees and manages its own subscriptions and has its own independent sender-email settings.
  多用户登录：可以自助注册账号（邮箱+密码+邀请码）；每个账号只能看到/管理自己的订阅，发件邮箱设置也各自独立。
- Registration requires an invite code, as an extra safeguard on top of network-level access control (Tailscale/SSH tunnel/VPN) — auto-generated on first run into `data/invite_code.txt`, or set your own via `REGISTER_INVITE_CODE` in `.env`.
  注册需要邀请码，作为网络层访问控制（Tailscale/SSH隧道/VPN）之外的额外一道保险——首次启动自动生成在 `data/invite_code.txt`，也可以在 `.env` 里用 `REGISTER_INVITE_CODE` 自定义。
- Registration now requires email verification: submit username + email + password + invite code, then enter the 6-digit code emailed to you to finish creating the account. Codes expire after 10 minutes, allow 5 attempts, and can be resent (60-second cooldown).
  注册改为需要邮箱验证：提交用户名+邮箱+密码+邀请码后，填入发到邮箱的6位验证码才算注册成功。验证码10分钟有效、最多试5次，可以重新发送（60秒冷却时间）。
- Log in with either your username or your email address.
  登录支持用户名或邮箱。
- Forgot-password flow: request a verification code by username or email, then use it to set a new password. The response is identical whether or not the account exists, to avoid revealing registered accounts.
  找回密码：用用户名或邮箱申请验证码，验证码对了就能设置新密码。不管账号存不存在都显示同一句提示，避免暴露哪些账号已注册。
- A new system-level sender account (`SYSTEM_SENDER_EMAIL`/`SYSTEM_SENDER_PASSWORD`/`SYSTEM_SMTP_*` in `.env`) sends these verification emails — separate from each user's own per-account sender settings.
  新增一个系统级发件账号（`.env` 里的 `SYSTEM_SENDER_EMAIL`/`SYSTEM_SENDER_PASSWORD`/`SYSTEM_SMTP_*`），专门用来发这些验证码邮件，跟每个用户自己的发件设置是分开的。
- The Settings page's account card now shows your username/email plainly, with password-changing tucked behind a collapsible "Change password" toggle to save space.
  设置页的账号卡片现在直接显示用户名/邮箱，"修改密码"收起在一个可展开的按钮后面，省地方。
- Pre-existing subscriptions/settings from before this upgrade are automatically adopted by the first account that successfully registers.
  升级前已有的订阅/设置，会被第一个注册成功的账号自动认领。
- The packaged macOS/Windows apps now bundle the JCR impact-factor/quartile data file, so it works out of the box instead of only when running from source.
  打包版的 macOS/Windows 程序现在会自带 JCR 影响因子/分区数据文件，不再只有源码运行才能用上。
- A new subscription's first check now searches two batches — the 10 most relevant articles from the last 5 years, and the 20 most recent regardless of date — merging and deduplicating them, with each article tagged as "most relevant" and/or "most recent" in the UI and email.
  新订阅第一次检查现在会查两批——近5年内最相关的10篇，以及不限时间最新的20篇——合并去重后一起作为入门文献，每篇文章在网页和邮件里都会标注属于"最相关"和/或"最新"。
- A unified reading list across all your subscriptions: save articles of interest from any subscription's article list, and manage them all from a new "Reading list" page (mark as read, remove).
  新增跨所有订阅的统一待阅读清单：可以在任意订阅的文献列表里把感兴趣的文章加入清单，在新的「待阅读」页面统一管理（标记已读、移除）。
- Alert emails now include a "select articles to add to your reading list" link — no login needed. Clicking it opens a page (still without login) listing that email's articles with checkboxes, so you can pick which ones to save in one submission.
  提醒邮件里新增"选择要加入待阅读的文献"链接，不需要登录——点开后是一个（同样不需要登录的）勾选页面，列出这封邮件里的文章，勾选想要的几篇一次性提交即可。
- New optional `APP_BASE_URL` setting in `.env` for the reading-list email link (the app doesn't otherwise know its own externally-reachable address); if left unset, emails still send normally, just without that link.
  `.env` 新增可选的 `APP_BASE_URL` 配置项，用于待阅读邮件链接（程序本身不知道自己对外的访问地址）；不配置的话邮件照常发送，只是没有这个链接。

### Changed
- Expired pending-registration and password-reset requests are now swept away hourly by a background job, so they don't accumulate indefinitely.
  过期的待验证注册请求和找回密码请求现在会被一个后台任务每小时清理一次，不会无限堆积。

### Fixed
- Closed several IDOR-style gaps where any logged-in-less visitor could edit/pause/delete/poll any subscription by guessing its URL — every subscription route now checks ownership.
  修复了此前任何人改一下网址里的编号就能编辑/暂停/删除/触发别人订阅的漏洞——所有订阅相关的路由现在都会校验归属。

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
