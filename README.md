# 📚 PubMed Alert

按关键词 / 期刊 / 作者订阅 PubMed 新文献，定期（或实时）通过邮件推送给你，并标注 Scimago (SJR) 期刊分区作为参考。

Subscribe to new PubMed articles by keyword / journal / author, and get them emailed to you
(instantly or as a digest), annotated with Scimago (SJR) journal quartiles for reference.

> 当前定位：小范围自用/分享，本地运行，不含用户注册系统。以后要部署到你自己的服务器上，直接把整个文件夹搬过去、装依赖即可，代码不需要改。
> Current scope: small-scale personal/shared use, runs locally, no user registration system.
> When you later deploy it to your own server, just copy the folder over and install dependencies
> — no code changes needed.

---

## 1. 功能 Features

- 🔍 按关键词、期刊、作者组合检索 PubMed 新文献（也支持直接写高级检索式）
  Search new PubMed articles by keyword / journal / author combinations (or write a raw advanced query)
- 📧 通过你自己的 Gmail 账号发送邮件通知
  Sends notification emails via your own Gmail account
- ⏱ 每个订阅可单独设置频率：有新文献立即发送 / 每天 / 每3天 / 每周汇总
  Each subscription can have its own frequency: instant / daily / every 3 days / weekly digest
- 🏷 邮件中标注 Scimago (SJR) 期刊分区（Q1–Q4）作为影响力参考
  Emails are annotated with Scimago (SJR) journal quartiles (Q1–Q4) as an influence reference
- 🌐 简单的网页界面管理订阅（增删改查、立即检查、查看已发现的文献）
  A simple web UI to manage subscriptions (CRUD, poll now, view discovered articles)
- 🌏 界面支持中文 / English / 日本語，右上角随时切换
  UI available in Chinese / English / Japanese — switch anytime from the top-right corner
- ⚙️ Gmail、NCBI API Key 都在网页「设置」页面配置，密码加密存储，不需要手动编辑配置文件；每个订阅只需要按需要发送的时机检索，不会做无意义的频繁请求
  Gmail and the NCBI API Key are configured on the web "Settings" page — the password is stored
  encrypted, no manual config-file editing needed; each subscription is only searched right when
  it's due to send, no wasted requests
- 🤖 预留 AI 总结接口（`app/summarizer.py`），接入大模型后邮件会自动带上每篇文章的一句话总结
  An AI-summary interface is reserved (`app/summarizer.py`) — once wired to an LLM, emails will
  automatically include a one-line summary per article

---

## 2. 快速开始 Quick Start

### 2.1 安装依赖 Install dependencies

```bash
cd pubmed_alert
pip install -r requirements.txt
```

### 2.2 运行 Run

```bash
python run.py
```

然后浏览器打开 Open your browser at: **http://127.0.0.1:8000**

第一次运行会自动创建本地数据库 `data/subscriptions.db`，不需要手动建表。右上角可以切换界面语言（中文 / English / 日本語）。

The local database `data/subscriptions.db` is created automatically on first run — no manual setup
needed. Switch the UI language (Chinese / English / Japanese) from the top-right corner.

### 2.3 配置 Gmail 发信 Configure Gmail sending

打开网页后，点击顶部导航的「设置 Settings」，填入 Gmail 地址和应用专用密码（见下方 Gmail 配置指南）后保存。可以用页面上的「发送测试邮件」按钮验证配置是否正确。

Open the app, click "Settings" in the top nav, and fill in your Gmail address and App Password
(see the Gmail setup guide below), then save. Use the "Send test email" button on that page to
verify the configuration works.

---

## 3. Gmail 配置指南 Gmail Setup Guide

Gmail 不允许直接用你的登录密码通过第三方程序发送邮件，需要生成一个专用的 **App Password（应用专用密码）**。

Gmail doesn't allow third-party programs to send mail with your regular login password — you need
to generate a dedicated **App Password**.

1. 打开 https://myaccount.google.com/security，确保已经开启"两步验证 (2-Step Verification)"（App Password 功能必须先开启两步验证才可用）。
   Open https://myaccount.google.com/security and make sure "2-Step Verification" is turned on
   (App Passwords require it).
2. 打开 https://myaccount.google.com/apppasswords，创建一个新的应用专用密码（名称随便填，比如 "PubMed Alert"）。
   Open https://myaccount.google.com/apppasswords and create a new App Password (name it anything,
   e.g. "PubMed Alert").
3. 复制生成的 16 位密码（形如 `abcd efgh ijkl mnop`），粘贴到网页「设置」页面的"应用专用密码"栏，连同 Gmail 地址一起保存。
   Copy the generated 16-character password (like `abcd efgh ijkl mnop`) into the "App Password"
   field on the web Settings page, along with your Gmail address, then save.

⚠️ 密码保存后会加密存进本地数据库（`data/subscriptions.db`），加密密钥是程序自动生成并保存在 `data/app_secret.key` 里的——这两个文件都不要分享给别人或提交到 git（已经在 `.gitignore` 里排除了）。也永远不要把密码粘贴到聊天记录或截图里。

⚠️ Once saved, the password is stored encrypted in the local database (`data/subscriptions.db`);
the encryption key is auto-generated and kept in `data/app_secret.key`. Never share either of these
files or commit them to git (already excluded via `.gitignore`) — and never paste the password into
chat logs or screenshots.

---

## 4. Scimago (SJR) 期刊分区数据 Journal Ranking Data

PubMed 本身不提供影响因子或分区数据，官方 JCR / 中科院分区都是付费数据源。这里用免费公开的 **Scimago Journal Rank (SJR)** 作为近似替代——**不是官方数据，仅供参考**。

PubMed itself has no impact-factor/quartile data, and official JCR / CAS partitions are paid data
sources. This project uses the free, public **Scimago Journal Rank (SJR)** as an approximation —
**not official data, for reference only**.

Scimago 网站有人机验证，无法用程序自动下载，需要手动下载一次：

Scimago's site has bot-protection, so it can't be downloaded automatically — you need to grab it
manually once:

1. 打开 https://www.scimagojr.com/journalrank.php
2. （可选）选择你关心的学科分类，或者留空看全部期刊 (optional) filter by subject category, or leave blank for all journals
3. 点击页面右下角的 "Download data" 按钮，会下载一个 `scimagojr <year>.csv` 文件
   Click the "Download data" button near the bottom of the page — downloads a `scimagojr <year>.csv` file
4. 把这个文件重命名为 `sjr_cache.csv`，放到本项目的 `data/` 文件夹下
   Rename it to `sjr_cache.csv` and place it in this project's `data/` folder
5. 重启程序即可生效（首页顶部的黄色提示会消失）
   Restart the app to pick it up (the yellow banner on the homepage will disappear)

不做这一步也完全不影响其他功能，只是邮件里不会显示分区标签。建议每年更新一次这个文件。

Skipping this step doesn't break anything else — emails will simply omit the quartile badge.
It's a good idea to refresh this file about once a year.

---

## 5. 使用说明 How to Use

1. 打开首页，点击 "新建订阅 New Subscription"。
   Open the homepage and click "New Subscription".
2. 填写关键词 / 期刊 / 作者（每行一个，任意组合，留空即不作为筛选条件）。想写复杂检索式的话，用"高级：自定义 PubMed 检索式"这一栏，会覆盖上面三项。
   Fill in keywords / journals / authors (one per line, any combination — leave blank to skip that
   filter). For complex queries, use the "Advanced: raw PubMed query" field, which overrides the three above.
3. 填写收件邮箱和发送频率，保存。
   Fill in the recipient email and frequency, then save.
4. 点击 "立即检查 Poll now" 可以马上跑一次检索，在 "查看文献 View articles" 里能看到抓到的结果（不需要等待定时任务）。
   Click "Poll now" to run a search immediately — see the results under "View articles" without
   waiting for the scheduled job.
5. 程序内部每15分钟醒一次，但只会对"到期"的订阅去检索 PubMed 并发送——检索的节奏完全由每个订阅自己的发送频率决定，不需要单独设置轮询间隔。
   Internally, the app wakes up every 15 minutes, but only searches PubMed and sends for
   subscriptions that are actually "due" — the search cadence is entirely determined by each
   subscription's own frequency, no separate poll-interval setting needed.

### 首次订阅 vs 后续更新 First subscription vs. ongoing updates

新建订阅第一次到期检查时，会按**相关度**取近 **5 年**内最相关的 **10 篇**文献作为"入门文献"（新订阅从未发送过，永远视为"已到期"，所以会立刻拿到这批文献，不需要等）；从第二次检查开始，改为按**发表日期**取最新更新的文献（和之前的行为一样）。

The first due-check for a brand-new subscription fetches the **10 most relevant** articles from
the **last 5 years**, sorted by relevance, as a "starter" batch (a subscription that's never been
dispatched is always considered "due", so this happens right away, no waiting). From the second
check onward, it switches to fetching the newest articles by **publication date** (same as before).

### 发送频率说明 Frequency semantics

- **immediate**：每次轮询后，只要发现了未发送过的新文献，立刻发一封邮件。
  Every poll cycle, if there are unsent new articles, send them right away.
- **daily / every_3_days / weekly**：把这段时间内新发现的文献攒到一起，凑够周期后一次性发一封汇总邮件；期间没有新文献则不发送（不会收到空邮件）。
  Accumulate newly found articles over the period, then send one digest email when it's due;
  if nothing new was found, no email is sent (never an empty digest).

---

## 6. 项目结构 Project Structure

```
pubmed_alert/
├── run.py                  # 启动入口 entry point
├── .env.example             # 仅用于旧版迁移，正常使用不需要 legacy migration source only
├── requirements.txt
├── data/                    # 本地数据库 + SJR缓存 + 加密密钥（gitignored）DB + SJR cache + secret key (gitignored)
└── app/
    ├── main.py               # FastAPI 路由 / web UI routes
    ├── config.py             # 基础配置 + 加密密钥管理 base config + secret key management
    ├── db.py                 # 数据库模型 (Subscription, SeenArticle, AppSettings)
    ├── settings.py           # 全局设置读取/迁移逻辑 settings read/migration logic
    ├── crypto.py             # 密码字段加解密 field-level encryption
    ├── i18n.py                # 界面多语言翻译 UI translations (zh/en/ja)
    ├── pubmed.py             # NCBI E-utilities 客户端 client
    ├── journal_rank.py        # Scimago SJR 加载与匹配 loader & matcher
    ├── mailer.py              # Gmail 发信 sending
    ├── summarizer.py          # AI 总结接口占位 reserved AI-summary interface
    ├── scheduler.py           # 定时轮询 + 发送逻辑 polling & dispatch scheduler
    ├── templates/             # 网页 & 邮件 HTML 模板
    └── static/                # CSS
```

---

## 7. 后续可扩展方向 Possible Future Extensions

- 接入大模型 API，在 `app/summarizer.py` 里实现 `summarize()`，邮件会自动带上每篇文章的 AI 总结（函数里已经写好了示例代码注释）。
  Wire up an LLM API in `app/summarizer.py`'s `summarize()` — emails will automatically include an
  AI summary per article (example code is commented in the file).
- 部署到你自己的云服务器：用 `Docker` 打包，或直接 `nohup python run.py &` / `systemd` 常驻运行。调度器跑在进程内部，不需要额外配置系统 cron。
  Deploy to your own server: package with Docker, or just run it persistently via
  `nohup python run.py &` / a `systemd` service. The scheduler runs inside the process, so no
  extra system cron setup is needed.
- 如果以后真的要开放给更多人注册使用，建议改成 Google OAuth 登录 + Gmail API 发信，而不是存储每个用户的 Gmail 密码。
  If this ever needs to open up to public registration, switch to Google OAuth login + the Gmail
  API for sending, instead of storing each user's Gmail password.
