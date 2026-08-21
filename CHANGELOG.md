# Changelog

This file documents notable changes to this project. Format follows
[Keep a Changelog](https://keepachangelog.com/), version numbers follow
[Semantic Versioning](https://semver.org/).

本文件记录本项目每个版本的重要变化。格式参照 [Keep a Changelog](https://keepachangelog.com/)，版本号规则参照 [语义化版本 SemVer](https://semver.org/lang/zh-CN/)。

## [1.3.0] - 2026-08-22

### Added
- Optional, per-user AI features, billed to each user's own account: a 1-2 sentence plain-language summary for every new article, a 0-100 AI relevance score against the subscription's topic, automatic title translation, English keyword extraction, a natural-language-to-PubMed-query generator on the subscription form, and a once-a-month per-subscription "trend digest" email synthesizing that month's articles.
  新增可选的、按用户自己账号计费的 AI 功能：为每篇新文献生成 1-2 句话总结、0-100 的相关性打分、自动翻译标题、提取英文关键词、在订阅表单里用大白话生成 PubMed 检索式，以及每个订阅每月一封的"趋势总结"邮件。
- AI provider choice on the Settings page: Claude (Anthropic), OpenAI, Google Gemini, DeepSeek, Qwen, xAI Grok, Doubao, or a custom OpenAI-compatible endpoint — pick one, paste your own API key and model name. Leaving it unset disables all AI features with no errors.
  「设置」页面可以选择 AI 供应商：Claude (Anthropic)、OpenAI、Google Gemini、DeepSeek、通义千问、xAI Grok、豆包，或自定义的 OpenAI 兼容接口——填自己的 API Key 和模型名字即可；不填就不启用任何 AI 功能，不会报错。
- Alert and trend-digest emails are English-only when the subscription owner's interface language is English, and bilingual (English + Chinese/Japanese) otherwise; AI-generated summaries follow the same rule, article abstracts are never translated, and AI-extracted keywords are always English.
  提醒邮件和趋势总结邮件：订阅所有者界面语言是英文就发纯英文，是中文/日文就发英文+对应语言双语；AI 生成的总结遵循同样的规则，文献摘要原文永远不翻译，AI 提取的关键词永远只用英文。
- Pending articles are now sent in order of AI relevance score (highest first) when available, falling back to the original discovery-time order otherwise.
  待发送的文献现在会按 AI 相关性打分从高到低排序（没有打分的话回退到原来按发现时间的顺序）。
- Alert emails cap at 20 fully-rendered articles to avoid being clipped by mail providers like Gmail on large batches; any remaining articles get a "view full list" link to the web page instead.
  提醒邮件最多完整展示 20 篇文献，避免一次性文献太多时被 Gmail 等邮箱服务商截断；超出的部分改成一个"查看完整列表"的网页链接。
- Editing a subscription's keywords/journals/authors/custom query now resets it to send one starter batch on the next check (like a new subscription), instead of treating every historical match under the new criteria as newly found.
  编辑订阅的关键词/期刊/作者/自定义检索式后，下次检查会像新订阅一样只发一批入门文献，而不是把新检索条件匹配到的所有历史文献都当作新发现。
- Unpaywall and AI lookups for newly-found articles now run concurrently instead of one at a time, substantially speeding up checks that discover many new articles at once.
  新发现文献的 Unpaywall 查询和 AI 生成内容现在并发执行，不再一篇篇排队，一次发现很多新文章时检索速度明显加快。
- `prompt_lab/`: a development-only scaffold (sample articles + a runner script) for testing and tuning the AI prompts in `app/ai_prompts.py`; not part of the running app and makes no real API calls unless explicitly configured.
  新增 `prompt_lab/` 开发用文件夹（真实文章样本 + 跑分脚本），用来测试/调优 `app/ai_prompts.py` 里的提示词；不属于线上程序运行的一部分，不主动配置的话不会产生真实调用。

### Changed
- Reverted the 1.2.1 comma/enumeration-comma/semicolon keyword separators — some journal names legitimately contain a comma (e.g. "Proceedings of the National Academy of Sciences, USA"), so splitting on comma could cut a journal name in half and break its search. Keywords/journals/authors are newline-separated only again.
  撤回了 1.2.1 版本"关键词支持逗号/顿号/分号分隔"的功能——有些期刊名字本身就带逗号（比如 "Proceedings of the National Academy of Sciences, USA"），按逗号拆分会把期刊名切开导致搜不到。关键词/期刊/作者恢复成只按换行分隔。
- The IF (impact factor) badge on the web pages is now color-coded by value (red >10, orange 5-10, yellow 3-5, green <3) instead of a single fixed color.
  网页上的影响因子（IF）徽章现在会按数值分档上色（>10 红、5-10 橙、3-5 黄、<3 绿），不再是固定的一种颜色。

### Fixed
- Fixed a bug where the Settings page's "sender email" and "AI features" sections — two separate forms both posting to `/settings` — would silently wipe each other's saved values, since a submitted form only carries its own fields. They now post to separate routes (`/settings` and `/settings/ai`).
  修复了「设置」页面"发件邮箱"和"AI 功能"两个表单会互相清空对方已保存内容的 bug——两个表单都提交到同一个 `/settings` 路由，而提交表单只会带上表单自己的字段。现在分别提交到独立的路由（`/settings` 和 `/settings/ai`）。
- Added tolerant JSON parsing and a larger output token limit for AI responses, reducing intermittent failures (missing summary/relevance/keywords on some articles but not others) seen with providers whose OpenAI-compatible mode is less strict about output format.
  给 AI 回复增加了更宽容的 JSON 解析和更大的输出长度上限，减少了部分供应商（OpenAI 兼容模式对输出格式要求没那么严格）偶尔出现的"有的文章有总结/相关性/关键词，有的没有"的问题。

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
