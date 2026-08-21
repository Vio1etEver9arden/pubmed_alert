# 项目备忘（给 Claude 用，跨电脑同步）

这份文件放在项目根目录，会被 Claude Code 在每次打开这个项目时自动读取，用来在换电脑/换会话时
保留上下文。内容是持续维护的"当前状态 + 未完成事项"，不是完整聊天记录；旧的、已解决的条目应该
被删掉或改写，而不是无限堆积。

## 当前版本

- v1.3.0（`app/__init__.py` 里的 `__version__`）——**还没 push 到 GitHub**，只在这台本地机器上
  （v1.2.1 已经确认 push 过了）。这个版本号覆盖：**按用户自愿开启、多供应商的 AI 功能**（总结/
  相关性打分/标题翻译/关键词提取/自然语言生成检索式/月度趋势总结，见下面单独一节）、影响因子
  徽章按数值分档上色、邮件按用户界面语言决定纯英文还是双语、待发送文献按 AI 相关性排序、邮件
  最多完整展示20篇文献（超出的改成"查看完整列表"链接）、编辑订阅关键词会重置成"发一批入门
  文献"、Unpaywall/AI 查询改成并发执行、修了几个用户在真实使用中发现的 bug（见下面单独一节）。
  **撤回**了 1.2.1 里"关键词支持逗号/顿号/分号分隔"这个功能（期刊名字本身可能带逗号，按逗号拆
  会拆错）。见 `CHANGELOG.md` 的 `[1.3.0]` 条目。
- v1.2.1：RIS 引文导出、文献列表和待阅读清单加搜索框、「设置」页一键导出个人数据备份（JSON）、
  文献1–5星阅读优先级、开放获取全文 PDF 链接（Unpaywall）、同一文章命中多个订阅时的邮件标注、
  第一批自动化测试（`tests/` 目录，pytest）。
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

**这个账号现在还真的配置了 AI**（`ai_backend=openai_compatible`，供应商是 Google Gemini，型号
`gemini-3.6-flash`，Key 是加密存的真实值）——以后如果要写脚本/测试直接读写这个账号的
`AppSettings` 行，**只做只读查询是安全的**，但绝对不要写一个会真的触发 `app.ai.enrich_article`
之类函数的脚本去跑这个账号的数据（会真的消耗用户自己的 API 额度/费用），跟"不要在真实数据库上
做破坏性测试"是同一条原则的延伸。

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

## AI 功能（v1.3.0 新增，按用户自愿开启、多供应商）

- **架构**：`app/ai.py` 是唯一对外接口（`is_configured`/`enrich_article`/`generate_query`/
  `write_trend_digest`/`test_connection`），内部按 `AppSettings.ai_backend`
  （只有两个取值："anthropic" 或 "openai_compatible"）转发给
  `app/ai_backends/anthropic_backend.py` 或 `app/ai_backends/openai_compatible_backend.py`。
  Claude 走官方 `anthropic` SDK；OpenAI/Gemini/DeepSeek/通义千问/Grok/豆包全部走同一个
  `openai_compatible_backend.py`（用 `openai` 这个 Python 包，只换 `base_url`）——这几家官方
  文档都确认支持 OpenAI 兼容调用方式，**不是**给每家单独写的对接代码。所有实际发给模型的
  提示词文字集中在 `app/ai_prompts.py` 一个文件里，方便以后单独调优。
- **完全按用户自愿开启，没有系统级共享 key**：`AppSettings` 上的 `ai_backend`/
  `ai_provider_preset`（纯 UI 用，记录下拉框选的品牌）/`ai_base_url`/`ai_api_key_enc`
  （加密，仿 `sender_password_enc` 写法）/`ai_model`（自由文本，不做下拉限定死列表，因为
  模型名字更新很快）。`ai.is_configured()` 没填 key 就返回 False，调用方（`scheduler.py`）
  无条件调用这几个函数，未配置时直接返回 `None`，不报错、不影响主流程——跟 `unpaywall.lookup()`
  是同一套"锦上添花、失败即跳过"的哲学。
- **豆包（火山方舟 Ark）没有一手文档验证过**，只查到二手资料佐证；而且它的"模型名字"字段实际上
  要填控制台创建的"推理接入点ID"（`ep-` 开头），不是模型名——这条在设置页有专门提示，用户应该
  先点"测试 AI 连接"确认。Gemini 官方文档自己写明"OpenAI 兼容层还在 beta"，实测也确实碰到过
  不稳定的输出（见下面"已知问题 / 已修复的 bug"）。
- **语言规则**：邮件（含月度趋势总结）跟着订阅所有者的 `AppSettings.ui_language` 走——英文界面
  发纯英文，中/日界面发"英文+对应语言"双语（`app/mailer.py` 的 `target_langs()`）。摘要原文
  永远不翻译；AI 提取的关键词永远只用英文；标题翻译只在界面语言不是英文时才生成。`enrich_article`
  的 JSON schema 是动态的：只有 `target_langs` 长度>1 时才问模型要 `summary_local`/
  `translated_title` 这两个字段，省 token。
- **相关性打分只是主观参考，不是精确测量**：0-100 分是 AI 读完文章和订阅主题后的直觉判断，
  换个时间/换个模型分数会有浮动。**只用来排序，不用来过滤/隐藏邮件**——待发送文献现在按
  `ai_relevance_score DESC, first_seen_at ASC` 排序（`scheduler.py` 的 `dispatch_subscription`），
  没打过分的文章 `NULL` 会被 SQL 自然排到最后、回退成原来的按时间顺序，**不需要**额外判断
  "有没有配置AI"。
- **每篇文章的 AI 内容只在首次发现时生成一次，不会重试/回填**——跟 Unpaywall、JCR 分区完全
  同一套设计。`app/scheduler.py` 的 `poll_subscription()` 里，Unpaywall 查询和 AI 生成内容
  现在用 `ThreadPoolExecutor`（`MAX_ENRICHMENT_WORKERS=8`）并发跑，因为这两个都是纯读网络请求，
  不碰数据库会话；**数据库写入（`session.add`）必须留在主线程顺序执行**，并发只发生在
  `_fetch_enrichment()` 这一步。
- **每月一次的趋势总结**：`scheduler.py` 的 `send_trend_digests()`，用 `CronTrigger(day=1,
  hour=8)` 注册（故意不给 `next_run_time`，不想让"每月一次"的任务在每次程序重启时也跟着多跑
  一次）。抓取窗口是"距现在往前30天"的固定滑窗（`SeenArticle.first_seen_at`，不是 `pub_date`——
  后者是抓取自 PubMed 的自由文本，格式不稳定），不是"距上次发送以来"，所以某个月跳过不会导致
  下个月内容重复/遗漏。`last_trend_sent_at` 只在真的发出邮件后才更新。
- **自然语言生成检索式**：`form.html` 里用 `formaction`/`formnovalidate` 让"AI 生成检索式"
  按钮把整个表单提交到 `POST /subscriptions/new/suggest-query`（或
  `/subscriptions/{id}/suggest-query`），重新渲染同一个表单、把生成结果填进 `query_override`
  框——**不会自动保存**，用户还要手动点正常的保存/创建按钮。没走 AJAX，符合这个项目"服务端
  渲染表单"的一贯风格。
- **`prompt_lab/`**：开发用的提示词测试脚手架（`fixtures.py` 真实文章样本 + `run_comparison.py`
  跑分脚本），不属于 `app/` 也不会被 `pytest` 收集，没配置环境变量就不会有真实调用。用户说
  "先搭好框架，具体测哪些 prompt 变体以后再细聊"——目前只是个空壳，还没有真的做多个候选提示词
  互相对比的功能。

## 已知问题 / 已修复的 bug（都是用户拿真实数据测试出来的，不是我自己发现的）

- **设置页两个表单互相清空对方的值**（已修复）：「发件邮箱」和「AI 功能」曾经是两个 `<form>`
  但都提交到同一个 `/settings` 路由——浏览器提交表单只带自己的字段，另一半字段在 `Form(...)`
  里有默认值，会被 FastAPI 悄悄当成"用户填了空值"直接覆盖掉。现在分成 `/settings`（邮箱）和
  `/settings/ai`（AI）两个独立路由，各自只碰自己的字段。`tests/test_settings_isolation.py`
  专门盯着这个不要退化。
- **Gemini 偶尔返回截断/夹带多余文字的 JSON**（已缓解，不能保证 100% 不再发生）：现象是"有的
  文章有 AI 总结，有的没有"——不是随机的，日志里全是 `JSONDecodeError`。缓解措施：
  `app/ai_prompts.py` 新增 `parse_json_response()`，直接解析失败会依次尝试"去掉 ```json 代码块
  标记"、"截取第一个{到最后一个}之间的内容"再解析；`enrich_article` 的 `max_tokens` 从 1024
  调到了 4096（怀疑是"思考"消耗掉了太多输出预算，具体没有一手资料完全证实，只是实测调大之后
  好转）。真要 100% 稳定建议换 Claude——结构化输出是服务端强制保证格式的。
- **编辑订阅关键词会导致邮件发出接近100篇"新"文献**（已修复）：`update_subscription()` 以前
  完全不管检索条件变没变，编辑后 `initial_poll_done` 还是 True，下次轮询走增量分支（默认一次
  最多抓100篇），换了新关键词等于几乎全部文章对这个订阅来说都是"没见过的"。现在编辑时会比较
  新旧的关键词/期刊/作者/自定义检索式，真的变了才把 `initial_poll_done` 重置为 False（下次
  检查表现得像新订阅一样，只发一批入门文献，最多约30篇）。只改标签/收件邮箱/频率不会触发。
- **邮件文献太多显示不全**（已修复）：Gmail 等邮箱对邮件正文大小有硬性限制（约102KB），加了
  AI 总结/关键词/翻译标题之后单篇文章占用空间变大，二三十篇往上就有实测撞到这个上限的风险。
  现在 `app/mailer.py` 的 `EMAIL_MAX_ARTICLES = 20` 把邮件正文封顶在20篇完整展示，超出部分
  改成"查看完整列表"的网页链接（需要 `APP_BASE_URL` 才有链接，没配置就只显示文字提示）。

## 自动化测试

- `tests/` 目录，pytest，跑 `python3 -m pytest tests/ -v`（目前 80+ 个测试全绿）。
  `tests/conftest.py` 在任何 `app.*` 模块被 import 之前先把 `PUBMED_ALERT_DATA_DIR` 设成一个
  临时文件夹（测试永远不会碰到真实的 `data/subscriptions.db`），并且有一个 `autouse=True` 的
  fixture 把 `app.mailer.send_verification_email`/`send_digest`/`send_test_email` 全部换成空
  函数——**这一点很关键**：早期漏了这层 mock，导致跑测试时真的用 `.env` 里配置的真实 Gmail 账号
  往 `@example.com` 发了十几封验证码邮件（好在 `example.com` 是 RFC 2606 保留的不可送达域名，
  没真人收到，但确实产生了真实的outbound SMTP流量），修复后才安全。**AI 相关的测试
  （`tests/test_ai.py` 等）同理**——全部用 `monkeypatch` 换掉 `anthropic.Anthropic`/
  `openai.OpenAI`，永远不连真实的 AI API、不产生真实费用。
- `tests/test_ownership.py` 是最重要的一份，回归测试所有 IDOR/权限隔离逻辑（改 URL 编号操作
  别人订阅这类漏洞）。其余按主题拆分：`test_ai.py`/`test_ai_json_parsing.py`（AI 两条后端路径 +
  JSON 容错解析）、`test_relevance_sort.py`（按相关性排序+NULL回退）、`test_trend_digest.py`
  （月度到期判断+语言规则）、`test_email_truncation.py`（邮件20篇上限）、
  `test_subscription_edit.py`（编辑订阅重置首次检索标记）、`test_settings_isolation.py`
  （两个设置表单不互相清空），其余测纯逻辑（密码哈希、邀请码、验证码、RIS格式化、关键词拆分、
  跨订阅重复检测、JIF分档上色）。

## 未完成 / 待跟进的事项

1. **部署到服务器/云端，具体基础设施还没定下来**：登录系统做完了，但用户还没实际选定/配置服务器
   （有闲置电脑，倾向自建，但没动手）。讨论过 Oracle Cloud 永久免费、Google Cloud Always Free
   （e2-micro 也永久免费但要绑卡，稍有不慎会真扣费，用户对此有顾虑）。下次接着聊的话，从"自建
   服务器 + 部署这个已经做好登录的版本"这个方向继续：帮忙配置开机自启（systemd）、Tailscale
   远程访问、把 `.env` 里的 `REGISTER_INVITE_CODE` 设成一个好记的值。
2. **`prompt_lab/` 只是个空壳**：用户说会另外提供 API Key、以后再细聊具体要测哪些提示词变体，
   目前 `run_comparison.py` 只是跑一遍 `app/ai_prompts.py` 里已有的提示词，没有"多个候选互相
   对比"的功能。
3. **AI 功能刚上线不久，用户还在实际使用中持续发现边界情况**：目前每次用户反馈的问题基本都是
   真实使用中暴露出来的（见上面"已知问题/已修复的 bug"），预期后续可能还会陆续冒出类似的、需要
   针对真实数据现场诊断的问题，不是一次性能穷举完的。

## 项目本身是什么

一个本地跑的 PubMed 文献订阅提醒工具（FastAPI + APScheduler + SQLite），按关键词/期刊/作者
订阅新文献，定期发邮件，邮件里标注 JCR 影响因子/分区（可选），可选接入 AI 生成总结/相关性/
翻译/关键词。详细功能和使用方法看根目录的 `README.zh.md`（中文）/ `README.md`（英文）/
`README.ja.md`（日文），代码结构不算大（`app/` 目录下 Python 代码约 3700 行），直接读代码
即可，不需要在这里重复。
