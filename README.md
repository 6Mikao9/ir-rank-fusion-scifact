# 科学声明的证据文献检索：基于 RRF 的多路词法排名融合

信息检索原理课程的论文阅读与实验项目。主题 X 为 **排名融合（Rank Fusion）**，研究问题为：不同词法检索器的相关性、融合方法和候选截断，如何影响科学证据检索的质量与成本？

主论文：Cormack, Clarke, Büttcher. *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods*, SIGIR 2009, pp.758–759. [DOI](https://doi.org/10.1145/1571941.1572114) · [作者公开原文](https://cormack.uwaterloo.ca/cormack/cormacksigir09-rrf.pdf)。

本项目是课程范围的透明实现与扩展实验，不声称复现原论文的 TREC/LETOR 实验，也不把词法融合称为稠密与稀疏混合检索。

## 内容

- `reports/reading.tex`：论文阅读报告，ACM `acmart` 的 `sigconf` 双栏格式。
- `reports/project.tex`：实验报告，含真实结果、评价定义、复现协议与局限。
- `reports/references.bib`：参考文献。
- `presentations/`：两套约 10 分钟的中文 Beamer 源码与逐页讲稿。
- `src/rankfusion/`：BM25、词级/字符级 TF-IDF、RRF、加权 RRF、归一化分数融合、指标实现。
- `scripts/`：下载、实验、检索演示、结果复核、报告图表生成和 LaTeX 编译。
- `results/`：8 种方法的测试集指标、逐查询结果、TREC run、开发集调参、bootstrap、机器环境及图表。

## 快速复现

需要 Python 3.10+，普通 CPU 即可，不需要 GPU 或商业 API。

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/download_data.py
python -m unittest discover -s tests -v
python scripts/run_experiment.py
python scripts/verify_results.py
python scripts/export_report_assets.py
```

检索演示（从仓库根目录运行）：

```bash
python scripts/search.py "Vitamin D reduces the risk of fractures" --method rrf_char
python scripts/search.py "Vitamin D reduces the risk of fractures" --method bm25
```

具体参数见 `python scripts/search.py --help`。首次演示需要建索引，计时不能与已经预热的查询延迟混淆。

## 数据与防泄漏

使用 [BEIR SciFact 官方预处理包](https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip)。共有 5,183 篇科学文献、809 个带训练标注的查询和 300 个测试查询。下载脚本校验官方 ZIP MD5 `5f7d1de60b170fc8027bb7898e2efca1`，原始数据不放入 Git。原始任务来源见 [SciFact](https://github.com/allenai/scifact)，本项目只评价证据文献检索，不做支持/反驳分类。

从官方 809 个训练查询中，以种子 42 固定抽取 200 个作为开发集，其余 609 个未使用。RRF 参数与分数融合权重只按开发集选择，冻结后才读取测试 qrels。完整文献库用于建索引，TF-IDF 只在文献上 fit。测试查询无结果时也记零，所有指标按全部 300 个查询宏平均。文献 ID 与查询 ID 属于不同命名空间，不作 `qid == docid` 的过滤。

## 实测结果

下表为仓库保存的这一次 CPU 实验，详细数字以 `results/metrics.json` 为准。

| 方法 | nDCG@10 | Recall@100 | 串行平均查询 ms |
|---|---:|---:|---:|
| BM25 | 0.6596 | 0.8726 | 7.45 |
| Word TF-IDF | 0.6286 | 0.8916 | 7.32 |
| Char TF-IDF | 0.6547 | 0.9187 | 34.85 |
| RRF BM25 + word, k=60 | 0.6574 | 0.8882 | 14.92 |
| RRF BM25 + char, k=60 | 0.6662 | 0.9303 | 42.46 |
| RRF 三路, k=60 | 0.6637 | 0.9259 | 49.83 |
| 开发集调参加权 RRF | 0.6602 | 0.8726 | 14.92 |
| 开发集调参分数融合 | 0.6596 | 0.8726 | 14.88 |

BM25 + char 的 nDCG 差值为 0.006572，配对 bootstrap 95% 区间为 [-0.011928, 0.025550]，跨越零。因此只报告小幅数值改善，**不声称显著优于 BM25**。Recall@100 的数值提升没有另作显著性检验。增加 word 路并不保证提升，三路融合也未超过 BM25 + char。

这份 BM25 是明确写出的词法基线（不做词干化或停用词过滤），不等同于 BEIR Elasticsearch 的官方基线。单路候选深度固定 100，RRF 中缺失候选贡献零。融合延迟按分别测得的各路时间串行求和加融合开销，未假设并行执行。分数融合虽然开发集选出 alpha=1，当前实现仍计算两路，不能据此断言该方法在优化实现中必然更慢。

## 编译 LaTeX

报告沿用 ACM/SIGIR 对应的 `acmart[sigconf,nonacm]`，不伪造 ACM 录用或出版信息。中文使用 `ctex` 与 TeX Live 自带 Fandol 字体。建议 TeX Live 完整版或配置好按需安装的 MiKTeX，编译器选 **XeLaTeX**。

```bash
python scripts/build_reports.py
```

也可以在 `reports/` 目录运行 `xelatex reading.tex`、`bibtex reading`、再运行两次 `xelatex reading.tex`，对 `project.tex` 同样操作。展示稿在 `presentations/` 中各运行两次 XeLaTeX。图表为结果文件，编译时保持仓库目录结构。

## 课程使用说明

论文阅读、实验报告和两套展示材料均由 AI 辅助起草、编程与核验，保留此说明。提交者应核对课程的 AI 使用要求，理解公式、代码、结果及局限，并自行填写姓名与学号。仓库公开只完成代码与材料发布，不代表已经向教师或教学平台提交作业。课堂展示、报告上传渠道和截止日需以教师最终通知为准。

## 参考

- [RRF 原论文](https://doi.org/10.1145/1571941.1572114)
- [An Analysis of Fusion Functions for Hybrid Retrieval](https://arxiv.org/abs/2210.11934)
- [BEIR](https://arxiv.org/abs/2104.08663)
- [SciFact](https://aclanthology.org/2020.emnlp-main.609/)
- [ACM 官方模板](https://www.overleaf.com/latex/templates/association-for-computing-machinery-acm-sig-conference-proceedings-template/bmvfhcdnxfty)

本仓库不附原论文全文或重许可数据集。数据与模板的权利、许可分别归其原作者，下载和再分发遵循各自条款。

