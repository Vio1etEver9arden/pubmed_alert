# 项目备忘（给 Claude 用，跨电脑同步）

这份文件放在项目根目录，会被 Claude Code 在每次打开这个项目时自动读取，用来在换电脑/换会话时
保留上下文。内容是持续维护的"当前状态 + 未完成事项"，不是完整聊天记录；旧的、已解决的条目应该
被删掉或改写，而不是无限堆积。

## 当前版本

- v1.2.1（`app/__init__.py` 里的 `__version__`）——**还没 push 到 GitHub**，只在这台本地机器上
  （v1.2.0 已经确认 push 过了，`git log`/`origin/main` 对得上）。这个版本号覆盖：RIS 引文导出、
  关键词分隔符支持逗号/顿号/分号、文献列表和待阅读清单加搜索框、「设置」页一键导出个人数据
  备份（JSON）、文献1–5星阅读优先级、开放获取全文 PDF 链接（Unpaywall，见下面单独一节）、
  同一文章命中多个订阅时的邮件标注（见下面单独一节），以及**第一批自动化测试**（`tests/`
  目录，pytest，见下面单独一节）。见 `CHANGELOG.md` 的 `[1.2.1]` 条目。
- v1.2.0：完整的多用户登录系统（账号/session/邀请码/所有权校验）、注册改成两步邮箱验证、登录
  支持用户名或邮箱、找回密码、设置页密码区域折叠、首次检索改成"相关10篇+最新20篇"双批次、
  跨订阅统一的待阅读清单（网页勾选 + 邮件里不需要登录的"选择要加入待阅读的文献"链接）。
- v1.1.1：发件邮箱从 Gmail 专用改成通用 SMTP；macOS 打包改成正规 `.app`；`run.py` 加了重复启动
  检测。

**重要**：用户自己已经用真实邮箱 `du.yilin.q2@dc.tohoku.ac.jp` 注册过一个账号（在还没有
username 字段的时候注册的），加 username 列的迁移给它自动回填了一个占位用户名
`du.yilin.q2_1`（邮箱前缀+id）。这个账号下面已经有一条真实订阅（"Hnf1b"，看起来是他自己的研究
课题）和真实的发件邮箱配置——**这是用户的真实数据，不是测试数据，绝对不能删/清空**。以后测试
注册/登录相关功能时，一定要在隔离的临时数据库副本上测（backup real db、换一份空的测试、测完再
换回来），不能直接对着 `data/subscriptions.db` 做注册/登录的破坏性测试。用户大概率还不知道自己
被自动分配了这个占位用户名，如果他问起"我的用户名是什么"或者登录一直失败，提醒他这件事，並可以
建议他在设置页看一眼（当前 UI 还没做"改用户名"功能，只能改密码）。

## 这个仓库的约定（已经跟用户确认过，别再问一遍）

- **git commit 消息只用英文**，不用中英双语。
- **不要**在 commit 里加 `Co-Authored-By: Claude ...` 这一行——之前加过一次，导致 GitHub
  Contributors 页面多出一个无关联的头像，用户明确要求以后都不要加。
- `CHANGELOG.md` 里每条改动是**英文在前、中文紧跟其后**（两行一组）；`README.md` /
  `README.zh.md` / `README.ja.md` 是三个独立单语文件，不需要在文件内部搞双语。
- **`data/jcr_cache.csv`（Clarivate JCR 影响因子/分区数据）故意提交进 git、公开在这个仓库里**。
  这份数据本来是付费数据，正常情况下不该公开分发；用户在被明确告知"这是公开仓库，一旦提交无法
  彻底收回"之后，仍然确认要这么做，风险自己承担。**不要**因为这是付费数据就自作主张把它加回
  `.gitignore` 或从仓库里删掉——除非用户明确改变主意。

## 登录系统

因为要部署到服务器给多人各自用（各自的订阅、各自的发件邮箱），加了完整的多用户登录：

- `User`（账号，含 `username`）、`Session`（登录会话，cookie 存 token 原文，数据库只存哈希）、
  `PendingRegistration`（待验证的注册请求）、`PasswordReset`（找回密码请求）四张表；
  `Subscription`、`AppSettings` 都加了 `user_id`，所有路由都按当前登录用户过滤/校验所有权
  （修掉了原来"改个 URL 数字就能操作别人订阅"的漏洞）。
- **开放自助注册 + 邀请码 + 邮箱验证码**：任何人知道地址都能自己注册，但需要填邀请码，提交后还
  要输入发到邮箱的6位验证码才算注册成功（10分钟有效、5次机会、60秒冷却可重发）。邀请码在
  `data/invite_code.txt`（首次启动自动生成，或在 `.env` 里设 `REGISTER_INVITE_CODE` 自定义）。
- **系统级发件账号**（`.env` 里的 `SYSTEM_SENDER_EMAIL`/`SYSTEM_SENDER_PASSWORD`/`SYSTEM_SMTP_*`）
  专门发验证码邮件，跟每个用户自己在「设置」页配的发件邮箱是两回事——目前配的就是那个一直在用
  的 Gmail 账号。不配置的话注册/找回密码会直接报错，`on_startup()` 里会打日志提醒。
- 登录支持用户名或邮箱（大小写不敏感），找回密码同理用用户名或邮箱申请验证码。
- **旧数据自动认领**：某次升级后，第一个注册成功的账号会自动接管升级前遗留的、没有 owner 的
  订阅/设置。所以正确顺序永远是：**升级后先自己注册，再把邀请码分享给别人**，不然被别人抢先
  注册会把你的旧数据和发件邮箱密码带走。
- 密码用 `cryptography` 包自带的 Scrypt 哈希（没加新依赖）。
- **已知接受的取舍**：`/register` 的"邮箱已注册"提示本身就会暴露某个邮箱是否注册过，而
  `/forgot-password` 特意做成"不管账号存不存在都显示同一句提示"来防止这个信息泄露——这两者不
  一致是刻意接受的（重新做成完全一致会让 `/register` 的正常报错体验变差，收益不大），**不要**
  看到这个不一致就当成 bug 去"修"。
- **这个项目现在有登录了，但仍然不能直接暴露在公网**：注册是开放的，真正的访问控制还是要靠
  Tailscale/SSH隧道/VPN，邀请码只是多一道保险，不是替代品。
- 过期的 `PendingRegistration`/`PasswordReset` 由 `scheduler.py` 里一个每小时跑一次的独立
  定时任务清理（`cleanup_expired_auth_rows`），跟检查 PubMed 订阅那个心跳是分开的两个 job。
- 完整实现计划存档在 `~/.claude/plans/fancy-finding-scone.md`（跨会话备份，这台机器上才有，
  每次做新的大改动这个文件会被覆盖，不是历史记录）。

## 首次检索 + 待阅读清单

- `poll_subscription()`（`scheduler.py`）首次检索现在查两批（相关度前10 + 最新20，5年内限定
  只对"相关"那批生效），按 pmid 合并去重后只调一次 `fetch_details`——**这里有个坑**：两批检索
  结果如果有重叠，必须先去重再抓详情/插入，不然会因为 `seen_articles` 的
  `UniqueConstraint(subscription_id, pmid)` 在 commit 时报错，插入循环里额外用了一个
  `seen_this_batch` 集合兜底。`SeenArticle` 上的 `initial_relevant`/`initial_recent` 两个
  标记不互斥，历史上已经完成过首次检索的旧记录不会被回填这两个字段（没有可靠信号能判断，就是
  默认 False）。
- 待阅读清单是跨订阅统一的一个清单，没建新表，就是 `SeenArticle` 加了
  `saved_for_reading`/`saved_at`/`read_at` 三个字段，按 `Subscription.user_id` 查询。
  "移除"清单会把 `saved_at`/`read_at` 一起清空，不是只翻转 `saved_for_reading`。
- 邮件里"选择要加入待阅读的文献"是**先跳一个不需要登录的网页勾选，最后提交**（不是每篇文章一
  个独立的一键链接）——用户明确要求这样，原因是大部分邮件客户端会把邮件正文里真正可交互的
  `<form>`/复选框 strip 掉，没法指望邮件本身实现"勾选+提交"，所以邮件里只放一个链接，真正的
  多选表单在落地页上。这个链接用 `app/crypto.py` 里新加的 HMAC token（对
  `user_id`+`article_ids` 签名，派生自 `APP_SECRET_KEY`，不设过期时间）鉴权，不需要登录。
- 这个链接需要 `.env` 里配置 `APP_BASE_URL`（程序自己不知道对外访问地址）；不配置的话邮件照常
  发，只是没有这个链接，不是像 `SYSTEM_SENDER_EMAIL` 那样的硬性要求。

## 开放获取全文链接 + 跨订阅重复提醒（v1.2.1）

- `app/unpaywall.py`：查 [Unpaywall](https://unpaywall.org/) 免费 API，输入 DOI 返回开放获取
  全文 PDF 链接，查不到/没 DOI/没配置联系邮箱/请求出错都返回 `None`（内部自己 try/except，不
  抛异常）。按 Unpaywall 的要求每次请求要带一个联系邮箱，直接复用了 `.env` 里的
  `SYSTEM_SENDER_EMAIL`，没配置这个就直接跳过查询，不强迫用户为了这一个小功能单独再配一个。
- 查询时机是**首次发现文章时查一次，存进 `SeenArticle.oa_pdf_url`，之后不会重试**——所以老文章
  (这个字段上线之前就已经存在的 `SeenArticle` 行) 永远是 `None`，不会自动回填。用户问起某篇老
  文章为什么没有全文链接是预期行为，不是 bug；真要补，需要手写一个一次性脚本手动跑
  `unpaywall.lookup()` 回填。
- 跨订阅重复提醒是 `app/scheduler.py` 里的 `_cross_subscription_labels()`：发送邮件前查一下
  "这篇文章除了这个订阅，同一用户名下还有没有别的订阅也见过它"，查到的订阅名字列表临时贴在
  `row.duplicate_labels` 这个属性上给邮件模板用（不是数据库字段，发完这次邮件这个属性就没了，
  不会持久化）。按用户明确要求：**两边邮件都照常发，只是加一句提示**，不是"只发一次/去重"。
  这个函数按 `user_id` 过滤，不会跨用户泄露另一个人的订阅名字。

## 自动化测试（v1.2.1 新增）

- `tests/` 目录，pytest，跑 `python3 -m pytest tests/ -v`。`tests/conftest.py` 在任何
  `app.*` 模块被 import 之前先把 `PUBMED_ALERT_DATA_DIR` 设成一个临时文件夹（测试永远不会碰到
  真实的 `data/subscriptions.db`），并且有一个 `autouse=True` 的 fixture 把
  `app.mailer.send_verification_email`/`send_digest`/`send_test_email` 全部换成空函数——**这
  一点很关键**：早期漏了这层 mock，导致跑测试时真的用 `.env` 里配置的真实 Gmail 账号往
  `@example.com` 发了十几封验证码邮件（好在 `example.com` 是 RFC 2606 保留的不可送达域名，没
  真人收到，但确实产生了真实的outbound SMTP流量），修复后才安全。
- `tests/test_ownership.py` 是最重要的一份，回归测试所有 IDOR/权限隔离逻辑（改 URL 编号操作
  别人订阅这类漏洞）；其余文件测纯逻辑（密码哈希、邀请码、验证码、RIS格式化、关键词拆分、跨
  订阅重复检测）。

## 未完成 / 待跟进的事项

1. **部署到服务器/云端，具体基础设施还没定下来**：登录系统做完了，但用户还没实际选定/配置服务器
   （有闲置电脑，倾向自建，但没动手）。讨论过 Oracle Cloud 永久免费、Google Cloud Always Free
   （e2-micro 也永久免费但要绑卡，稍有不慎会真扣费，用户对此有顾虑）。下次接着聊的话，从"自建
   服务器 + 部署这个已经做好登录的版本"这个方向继续：帮忙配置开机自启（systemd）、Tailscale
   远程访问、把 `.env` 里的 `REGISTER_INVITE_CODE` 设成一个好记的值。

## 项目本身是什么

一个本地跑的 PubMed 文献订阅提醒工具（FastAPI + APScheduler + SQLite），按关键词/期刊/作者
订阅新文献，定期发邮件，邮件里标注 JCR 影响因子/分区（可选）。详细功能和使用方法看根目录的
`README.zh.md`（中文）/ `README.md`（英文）/ `README.ja.md`（日文），代码结构很小（`app/`
目录下总共约1300+行），直接读代码即可，不需要在这里重复。
