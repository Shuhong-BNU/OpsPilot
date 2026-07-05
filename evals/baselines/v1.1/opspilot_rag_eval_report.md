# OpsPilot RAG Retrieval Eval Report

## Environment

- Commit: `68819d007fc0f49e902e0e19f3411059f12a7817`
- Branch: `main`
- Evaluation Mode: Hybrid Retrieval
- Evaluation Status: PASS
- Dataset: `evals/datasets/opspilot_rag_cases.jsonl`
- Dataset Size: 10
- Python: 3.12.13
- Git Status: `## main...origin/main
 M app/services/retrieval_service.py
 M tests/test_retrieval_service.py
?? evals/`
- Known Sources: cpu_high_usage.md, disk_high_usage.md, memory_high_usage.md, service_unavailable.md, slow_response.md
- Retrieval Configuration: `{"dense_top_k": 6, "sparse_top_k": 6, "hybrid_top_k": 4, "rerank_top_k": 3, "milvus_host": "localhost", "milvus_port": 19530, "embedding_model": "text-embedding-v4", "sqlite_chunk_count": 21}`

## Summary

- Total Cases: 10
- Scorable Cases: 10
- Infrastructure Blocked Cases: 0
- Hit@3: 1.000
- MRR: 1.000
- Average Wall-Clock Latency: 1764.9 ms

## Stage Latency

- Dense Average: 1761.4 ms
- Sparse Average: 2.4 ms
- Rerank Average: 0.0 ms

## Case Results

| id | pass | first relevant rank | top3 sources | wall time |
| --- | --- | --- | --- | --- |
| rag_cpu_001 | yes | 1 | cpu_high_usage.md, disk_high_usage.md, cpu_high_usage.md | 4664 ms |
| rag_cpu_002 | yes | 1 | cpu_high_usage.md, cpu_high_usage.md, memory_high_usage.md | 2284 ms |
| rag_memory_001 | yes | 1 | memory_high_usage.md, memory_high_usage.md, memory_high_usage.md | 2281 ms |
| rag_memory_002 | yes | 1 | memory_high_usage.md, memory_high_usage.md, memory_high_usage.md | 2105 ms |
| rag_disk_001 | yes | 1 | disk_high_usage.md, memory_high_usage.md, cpu_high_usage.md | 876 ms |
| rag_disk_002 | yes | 1 | disk_high_usage.md, disk_high_usage.md, disk_high_usage.md | 859 ms |
| rag_service_001 | yes | 1 | service_unavailable.md, slow_response.md, cpu_high_usage.md | 847 ms |
| rag_service_002 | yes | 1 | service_unavailable.md, service_unavailable.md, cpu_high_usage.md | 2040 ms |
| rag_slow_001 | yes | 1 | slow_response.md, slow_response.md, cpu_high_usage.md | 847 ms |
| rag_slow_002 | yes | 1 | slow_response.md, slow_response.md, service_unavailable.md | 846 ms |

## Failure Analysis

- No retrieval misses among scorable cases.

## Infrastructure Warnings

- None.

## Metric Definitions

- Hit@3: case-level hit. A case scores 1 when at least one relevant source appears in top 3, otherwise 0.
- MRR: reciprocal rank of the first relevant source; 0 when no relevant source is retrieved.
- Wall-clock latency: runner-measured elapsed time around `retrieval_service.hybrid_search`.
- Stage latency: dense, sparse, and rerank latency reported by `RetrievalTrace`.
