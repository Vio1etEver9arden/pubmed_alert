# 项目备忘（给 Claude 用，跨电脑同步）

这份文件放在项目根目录，会被 Claude Code 在每次打开这个项目时自动读取，用来在换电脑/换会话时
保留上下文。内容是持续维护的"当前状态 + 未完成事项"，不是完整聊天记录；旧的、已解决的条目应该
被删掉或改写，而不是无限堆积。

## 当前版本

- v1.1.1（`app/__init__.py` 里的 `__version__`），已经 push 到 GitHub `main` 分支。
- 核心改动：发件邮箱从 Gmail 专用改成通用 SMTP（设置页可选 Gmail/QQ邮箱/163邮箱/Outlook/自定义）；
  macOS 打包改成正规 `.app`（`--windowed` + 本机自签名，不再弹终端窗口）；`run.py` 加了重复启动
  检测（已经在跑就直接打开浏览器，不报错）。详见 `CHANGELOG.md`。

## 这个仓库的约定（已经跟用户确认过，别再问一遍）

- **git commit 消息只用英文**，不用中英双语。
- **不要**在 commit 里加 `Co-Authored-By: Claude ...` 这一行——之前加过一次，导致 GitHub
  Contributors 页面多出一个无关联的头像，用户明确要求以后都不要加。
- `CHANGELOG.md` 里每条改动是**英文在前、中文紧跟其后**（两行一组）；`README.md` /
  `README.zh.md` / `README.ja.md` 是三个独立单语文件，不需要在文件内部搞双语。

## 未完成 / 待跟进的事项

1. **JCR 影响因子+分区 CSV 找不到**：用户记得自己整理过一份"2025 IF + JCR 分区"的 CSV，以为
   前一天晚上提交过，但翻遍 git 历史（4次提交）、reflog、stash、悬空对象，以及本地 `data/`
   目录和 Desktop/Downloads/Documents，都没找到——唯一提交过的 CSV 是 `data/sjr_cache.csv`
   （免费的 Scimago SJR 数据，列名是 `SJR`/`SJR Best Quartile`，跟 `app/journal_rank.py` 实际
   读取的 `data/jcr_cache.csv`（列名 `name/eissn/quartile/jif2026`）完全不是一回事）。最可能
   的原因：`.gitignore` 里写死排除了 `data/jcr_cache.csv` 这个文件名，就算本地做过也不会被
   git 提交。用户说要回家换电脑上找找看。**如果用户带着新版本的 CSV 回来**：核对一下它的列名
   是否匹配 `journal_rank.py` 期望的格式（`name, eissn, quartile, jif2026`），不匹配的话可能
   需要写个小转换脚本，而不是直接假设格式一样。

2. **部署到服务器/云端，还没定下来**：用户想让程序一直在后台跑，不用手动开着软件才能收到新文章
   提醒。讨论过 Oracle Cloud 永久免费（够用但注册/容量偶尔麻烦）、Google Cloud Always Free
   （e2-micro 也是永久免费，但要绑卡，稍微超出免费额度规则就会真的扣费，用户对这点有顾虑，
   查证过确实如此）、自建服务器（用闲置电脑/树莓派，零风险零月费，但需要用户自己有设备）。
   **用户目前倾向自建**（有闲置电脑），但还没实际动手配置。下次接着聊的话，从"自建"这个方向
   继续，可以帮忙配置开机自启（systemd）、Tailscale 远程访问；一定要提醒：这个项目**完全没有
   登录鉴权**，绝对不能把端口直接暴露在公网上。

## 项目本身是什么

一个本地跑的 PubMed 文献订阅提醒工具（FastAPI + APScheduler + SQLite），按关键词/期刊/作者
订阅新文献，定期发邮件，邮件里标注 JCR 影响因子/分区（可选）。详细功能和使用方法看根目录的
`README.zh.md`（中文）/ `README.md`（英文）/ `README.ja.md`（日文），代码结构很小（`app/`
目录下总共约1300+行），直接读代码即可，不需要在这里重复。
