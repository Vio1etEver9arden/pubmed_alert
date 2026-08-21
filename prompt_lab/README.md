# prompt_lab

这个文件夹是专门用来测试/调优提示词（prompt）的地方——不是 Claude Code 的"skill"，是
`app/ai_prompts.py` 里拼给 AI 模型的那段文字。这段文字直接决定 AI 回答的质量和消耗的 token
数量（=花的钱），跟这个程序本身运不运行没有关系，纯粹是开发时用来做实验的工具。

**不属于线上程序**：不会被 `app/` 里的任何代码 import，也不会被 `pytest` 收集（文件名不是
`test_*.py`），日常跑 `python3 -m pytest tests/` 不会碰到这个目录，更不会产生真实的 API 调用/
费用。

## 文件

- `fixtures.py` —— 几篇真实文章的 title/abstract 样本，专门用来看"这段摘要，AI 会怎么总结/
  打分/提取关键词"。跟 `tests/` 目录里的假数据不一样，这边的内容需要是真实、有实质信息量的
  文本，才能真正比较出提示词写法的好坏。
- `run_comparison.py` —— 拿 `fixtures.py` 的样本，走 `app/ai.py` 真实的调用路径（不是另外
  写一套逻辑），跑一遍当前 `app/ai_prompts.py` 里的提示词，把每次调用的原始输出打印出来。

## 怎么用

先设置好环境变量，指定要测哪个供应商/模型：

```bash
export PROMPT_LAB_BACKEND=anthropic          # 或 openai_compatible
export PROMPT_LAB_API_KEY=sk-...
export PROMPT_LAB_BASE_URL=...               # 只有 openai_compatible 才需要填
export PROMPT_LAB_MODEL=claude-haiku-4-5
python3 prompt_lab/run_comparison.py
```

**不配置任何环境变量的话，脚本会打印提示直接退出，不会产生真实调用**——避免不小心跑出真实
费用。

## 花费大概多少

每篇 `fixtures.py` 里的样本文章对应一次 `enrich_article` 调用（总结+相关性+关键词一起算），
用 Haiku 档位的模型，一次跑下来通常远低于 $0.01。具体多少钱取决于 `fixtures.py` 里放了几篇
样本、摘要有多长。

## 以后怎么测试不同的提示词写法

现在这个脚本只是"跑一遍当前 `app/ai_prompts.py` 里已经写好的提示词"，还没有"多个候选提示词
互相比较"的功能——这部分等你确定要具体测哪些方向（比如换一种问法、换一个模型、控制输出长度）
之后再一起加，不在这一轮里预先搭好。
