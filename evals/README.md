# OpsPilot Retrieval Evaluation

## v2：迁移后的离线回归评测

`evals/run_retrieval_eval.py` 对 `evals/datasets/opspilot_rag_cases.jsonl` 和 `evals/corpus/` 运行确定性离线评测。

```bash
cd apps/backend
uv run python ../../evals/run_retrieval_eval.py
```

评测复用生产 `KnowledgeRetrievalTool` 的以下逻辑：权限过滤、向量候选与 BM25L 候选的 RRF 融合、rerank 结果组装、引用和每一阶段 rank 证据。为了能在没有网络、Milvus 和模型密钥的 CI 环境中复现，只有三项外部依赖被替换为确定性本地 adapter：Milvus、embedding、Qwen rerank。

输出：

- `evals/results/opspilot_rag_eval_v2_results.jsonl`：逐 case 结果与 stage evidence。
- `evals/reports/opspilot_rag_eval_v2_report.md`：人可读报告。

指标：

- `Hit@1`：首位结果是否是任一相关来源。
- `Hit@3`：前三结果是否包含任一相关来源。
- `MRR`：第一个相关来源的倒数排名。
- `Recall@3`：前三结果找回的相关来源占全部相关来源的比例。

v2 不测线上 Qwen/Milvus 的质量、延迟或成本，也不测回答生成、Groundedness、AIOps 和 MCP。真实服务的 integration eval 是后续工作，必须与离线 CI 结果分开报告。

## v1 / v1.1：迁移前历史证据

`evals/baselines/v1/` 与 `evals/baselines/v1.1/` 保留旧 OpsPilot 检索架构的历史 artifact，不能与 v2 横向当作同一系统的质量对比，也不应被重写。
