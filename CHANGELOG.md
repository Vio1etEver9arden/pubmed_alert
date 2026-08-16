# Changelog

本文件记录本项目每个版本的重要变化。格式参照 [Keep a Changelog](https://keepachangelog.com/)，版本号规则参照 [语义化版本 SemVer](https://semver.org/lang/zh-CN/)。

This file documents notable changes to this project. Format follows
[Keep a Changelog](https://keepachangelog.com/), version numbers follow
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-08-17

### Added
- 按关键词 / 期刊 / 作者订阅 PubMed 新文献，支持即时或按周期汇总发送邮件。
- 邮件中标注官方 JCR 影响因子和分区（通过本地解析自己导出的 JCR PDF 获得，见 `scripts/parse_jcr_pdf.py`）。
- 网页界面管理订阅，支持中文 / English / 日本語。
- 通过 Gmail 发信，密码加密存储。
- Windows / macOS 独立打包支持（PyInstaller），方便分享给不用 Python 的人。
