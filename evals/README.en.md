# OpsPilot Retrieval Evaluation

## v2: migrated offline regression evaluation

`evals/run_retrieval_eval.py` evaluates the fixed dataset in
`evals/datasets/opspilot_rag_cases.jsonl` against `evals/corpus/`.

```bash
cd apps/backend
uv run python ../../evals/run_retrieval_eval.py
```

The evaluation executes the production `KnowledgeRetrievalTool` path for scope
filtering, BM25L, RRF fusion, rerank result shaping, citations, and per-stage
rank evidence. Milvus, remote embeddings, and Qwen reranking are replaced with
deterministic local adapters so the regression check can run without a network,
model credentials, or a Milvus service.

It writes case evidence to `evals/results/` and a readable report to
`evals/reports/`. Metrics are Hit@1, Hit@3, MRR, and Recall@3.

This is a deterministic code-regression check, not a claim about the quality,
latency, or cost of the production Milvus/Qwen deployment. Online integration
evaluation must be recorded separately.

## Historical baselines

`evals/baselines/v1/` and `evals/baselines/v1.1/` are frozen artifacts from
the pre-migration retrieval implementation. They are retained for provenance
and must not be overwritten or compared directly with v2.
