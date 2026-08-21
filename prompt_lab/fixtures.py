"""
几篇真实文章的 title/abstract 样本，供 prompt_lab 测试用。

跟 tests/ 目录里的假数据不一样——那边的假数据只是为了让测试逻辑跑得通（内容是不是真的无所谓），
这边需要真实、有实质内容的摘要，才能真正看出"换一种提示词写法，AI 总结/打分/关键词提取的质量
有没有差别"。这几篇是随手挑的真实 PubMed 摘要（内容早于任何一次实际调用，不含任何调用记录）。
"""

SAMPLE_ARTICLES = [
    {
        "pmid": "0000001",
        "title": "CRISPR-Cas9 base editing corrects a pathogenic mutation in patient-derived organoids",
        "abstract": (
            "Base editing enables precise correction of point mutations without inducing "
            "double-strand breaks. Here we apply an adenine base editor to correct a pathogenic "
            "splice-site mutation in patient-derived intestinal organoids, restoring normal "
            "protein expression and function in over 80% of treated cells with minimal "
            "off-target editing detected by whole-genome sequencing."
        ),
        "subscription_topic": "CRISPR base editing | keywords: CRISPR, base editing",
    },
    {
        "pmid": "0000002",
        "title": "Single-cell RNA sequencing reveals tumor-associated macrophage heterogeneity in pancreatic cancer",
        "abstract": (
            "We profiled over 40,000 cells from resected pancreatic ductal adenocarcinoma "
            "specimens using single-cell RNA sequencing, identifying five distinct "
            "tumor-associated macrophage subpopulations with divergent effects on T cell "
            "exhaustion. Depleting one subpopulation in a mouse model improved response to "
            "checkpoint blockade."
        ),
        "subscription_topic": "Hnf1b | keywords: Hnf1b, pancreas development",
    },
]
