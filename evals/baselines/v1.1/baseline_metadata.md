# OpsPilot RAG Baseline v1.1 Metadata

## Identity

- Baseline: v1.1
- Created At: 2026-07-05T15:17:20+08:00
- Git Commit: `68819d007fc0f49e902e0e19f3411059f12a7817`
- Evaluation Mode: Hybrid Retrieval
- Evaluation Status: PASS
- Dataset Size: 10
- Baseline v1.1 Established: YES

## Scope

- 本轮唯一业务修改: `app/services/retrieval_service.py` 中 `_sparse_search` 的 sparse query builder 从多 token AND 改为多 token OR；继续复用 `TOKEN_PATTERN`。
- 测试修改: `tests/test_retrieval_service.py` 增加 query-builder 最小覆盖。
- 未修改: FTS5 schema、tokenizer、SQLite SQL、dense retrieval、RRF、reranker、top_k、dataset、metrics。

## File Fingerprints

- Dataset SHA256: `16eb65a214b920afa743f8f5e80aadbfb5d078e828b26a3a147481800efb1770`
- Eval Runner SHA256: `1d4176050e62b9a6f726a8a8747188ebd1f5b8d43ab42e53d10fbd0a6b6a7646`
- v1.1 Results SHA256: `2023e5f8a1508f65c763306ddf3636dfa7cb66e688024f72e99f47e3c1ce28d4`
- v1.1 Report SHA256: `ca74f4218367490ee65f08de252643ff55e08c7e9bf2fc88e1914d2eaf6b5942`
- Modified Retrieval Service SHA256: `45a35d15239794c4424a250bcf6b07e8a6df636bffe1aead0c280a996c4490b1`
- Modified Retrieval Test SHA256: `248841615062486cb3e682354583b02763097481e1950045ee4047ed3d38a427`

## Metrics

- Total Cases: 10
- Scorable Cases: 10
- PASS Cases: 10
- FAIL Cases: 0
- INFRA_BLOCKED Cases: 0
- Hit@3: 1.000
- MRR: 1.000
- Average Wall-Clock Latency: 1764.9 ms
- Dense Latency Average: 1761.4 ms
- Sparse Latency Average: 2.4 ms
- Rerank Latency Average: 0.0 ms
- Sparse Non-Empty Cases: 4
- Sparse Relevant Hit Cases: 4

## Comparison With v1

- v1 Hit@3: 1.000 -> v1.1 Hit@3: 1.000
- v1 MRR: 0.950 -> v1.1 MRR: 1.000
- v1 Average Wall-Clock Latency: 1217.1 ms -> v1.1 Average Wall-Clock Latency: 1764.9 ms
- v1 Sparse Non-Empty Cases: 0 -> v1.1 Sparse Non-Empty Cases: 4
- v1 Sparse Relevant Hit Cases: 0 -> v1.1 Sparse Relevant Hit Cases: 4

## Notes

- v1.1 使用与 v1 相同 dataset 和 eval runner。
- v1.1 没有重新 ingestion，没有重建索引，没有修改 ground truth。
