# 📚 PubMed Alert

[English](README.md) · **中文** · [日本語](README.ja.md)

按关键词 / 期刊 / 作者订阅 PubMed 新文献，定期（或实时）通过邮件推送给你，并标注官方 JCR 影响因子和分区作为参考。

> 定位：小范围自用/分享，本地运行，不含用户注册系统。以后要部署到你自己的服务器上，直接把整个文件夹搬过去、装依赖即可，代码不需要改。

---

## 功能

- 🔍 按关键词、期刊、作者组合检索 PubMed 新文献（也支持直接写高级检索式）
- 📧 通过你自己的 Gmail 账号发送邮件通知
- ⏱ 每个订阅可单独设置频率：有新文献立即发送 / 每天 / 每3天 / 每周汇总
- 🏷 邮件中标注官方 JCR 影响因子和分区（Q1–Q4）作为影响力参考
- 🌐 简单的网页界面管理订阅（增删改查、立即检查、查看已发现的文献）
- 🌏 界面支持中文 / English / 日本語，右上角随时切换
- ⚙️ Gmail、NCBI API Key 都在网页「设置」页面配置，密码加密存储，不需要手动编辑配置文件

---

## 快速开始

### 方式一：用 Python 自己运行

```bash
cd pubmed_alert
pip install -r requirements.txt
python run.py
```

然后浏览器打开 **http://127.0.0.1:8000**。第一次运行会自动创建本地数据库。

### 方式二：使用别人打包好的程序（不用装 Python）

如果有人给了你一个 `PubMedAlert.exe`（Windows）或 `PubMedAlert`（Mac），直接双击运行即可，
浏览器会自动打开。如果你是要打包发给别人的那个人，看下面「打包给不会用 Python 的人」一节。

### 配置 Gmail 发信

打开网页后，点击顶部导航的「设置」，填入 Gmail 地址和应用专用密码（见下方），保存后可以用
「发送测试邮件」按钮验证配置是否正确。

---

## Gmail 配置指南

Gmail 不允许直接用你的登录密码通过第三方程序发送邮件，需要生成一个专用的**应用专用密码**。

1. 打开 [myaccount.google.com/security](https://myaccount.google.com/security)，确保已经开启
   「两步验证」（应用专用密码功能必须先开启两步验证才可用）。
2. 打开 [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)，创建一
   个新的应用专用密码（名称随便填，比如 "PubMed Alert"）。
3. 复制生成的 16 位密码，粘贴到网页「设置」页面，连同 Gmail 地址一起保存。

⚠️ 密码保存后会加密存进本地数据库。不要分享 `data/subscriptions.db` 或 `data/app_secret.key`
这两个文件给别人，也永远不要把密码粘贴到聊天记录或截图里。

---

## 影响因子 / JCR 分区数据（可选）

PubMed 本身不提供影响因子或分区数据。官方 **Journal Citation Reports (JCR)** 是 Clarivate 的
付费数据源，一般通过所在机构的订阅才能访问。这个项目不做任何抓取或绕过付费墙的操作——你需要
自己有访问权限。

1. 通过你机构的 Web of Science / JCR 访问权限，导出当年的 "Journal Impact Factor" 报告为 PDF。
2. 把 PDF 放到本项目的 `data/` 文件夹下。
3. 运行：
   ```bash
   pip install pdfplumber
   python scripts/parse_jcr_pdf.py "data/JCR Journal Impact Factor 2026.pdf"
   ```
4. 重启程序即可生效（首页顶部的黄色提示会消失）。

不做这一步也完全不影响其他功能，只是邮件里不会显示影响因子/分区标签。建议每年 JCR 更新后重新
导出一次。这是每人各自的事——每个人用自己的订阅权限生成自己的缓存文件，不会被分享或提交到 git。

---

## 使用说明

1. 打开首页，点击「新建订阅」。
2. 填写关键词 / 期刊 / 作者（每行一个，任意组合，留空即不作为筛选条件）。想写复杂检索式的话，
   用「高级：自定义 PubMed 检索式」这一栏，会覆盖上面三项。
3. 填写收件邮箱和发送频率，保存。
4. 点击「立即检查」可以马上跑一次检索，在「查看文献」里能看到抓到的结果，不需要等待定时任务。

新建订阅第一次检查时，会取近 **5 年**内最相关的 **10 篇**文献作为"入门文献"；之后每次检查只
发送新发表的文献。

**发送频率说明：**
- **立即发送**：发现新文献就立刻发一封邮件。
- **每天 / 每3天 / 每周**：把这段时间内新发现的文献攒到一起，凑够周期后一次性发送汇总邮件；
  期间没有新文献则不发送。

---

## 打包给不会用 Python 的人

如果对方不装/不会用 Python，可以用 `packaging/` 里的脚本把整个程序打包成一个独立的可执行文件；
对方拿到文件后直接双击运行，浏览器会自动打开，不需要装任何东西。**每个人独立运行自己的一份**，
各自有自己的数据库和 Gmail 配置。

打包必须在目标系统上进行（PyInstaller 不能跨平台编译）：

```powershell
# 在 Windows 上运行，产出 dist\windows\PubMedAlert.exe
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

```bash
# 在 Mac 上运行，产出 dist/mac/PubMedAlert
chmod +x packaging/build_mac.sh
./packaging/build_mac.sh
```

把那一个文件发过去就行。请对方先放进一个新建的空文件夹里再双击（不要在下载目录或压缩包里直接
运行）——运行后会在旁边生成 `data/` 文件夹存数据库。**macOS 用户注意**：Gatekeeper 会拦截未签
名的程序，第一次要在「访达」里右键选「打开」，不能直接双击。

每个接收者需要自己配置 Gmail 应用专用密码，以及（可选）自己的 JCR 数据——参考上面的对应章节。
