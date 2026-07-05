# OpsPilot RAG Baseline v1 Metadata

## Identity

- Baseline: v1
- Created At: 2026-07-05T14:44:18+08:00
- Git Commit: `68819d007fc0f49e902e0e19f3411059f12a7817`
- Evaluation Mode: Hybrid Retrieval
- Evaluation Status: PASS
- Dataset Size: 10
- Notes: v1 是 sparse query builder 修复前的原始 baseline；未做 sparse 修复。

## File Fingerprints

- Dataset SHA256: `16eb65a214b920afa743f8f5e80aadbfb5d078e828b26a3a147481800efb1770`
- Eval Runner SHA256: `1d4176050e62b9a6f726a8a8747188ebd1f5b8d43ab42e53d10fbd0a6b6a7646`
- v1 Results SHA256: `fb85f5acf825dcd0818a99cff5f0989a1bcd4fd2045c015b9c169a9d955e9020`
- v1 Report SHA256: `7948ef04391a71a9457983b5b212fbb714f49869c41e7e7be1546c765a57ba18`

## Metrics

- Total Cases: 10
- Scorable Cases: 10
- PASS Cases: 10
- FAIL Cases: 0
- INFRA_BLOCKED Cases: 0
- Hit@3: 1.000
- MRR: 0.950
- Average Wall-Clock Latency: 1217.1 ms
- Dense Latency Average: 1214.6 ms
- Sparse Latency Average: 1.7 ms
- Rerank Latency Average: 0.0 ms

## Index State

- Milvus URI: `http://localhost:19530`
- Milvus Database: `default`
- Milvus Collection: `biz`
- Milvus Entity Count: 21
- SQLite Database: `./data/opspilot.db`
- SQLite `document_chunks`: 21
- SQLite `document_chunks_fts`: 21

## Change State

- Business Code Modified For v1: No
- Eval Dataset Modified For v1: No
- Eval Runner Modified For v1: No
- Sparse Query Builder Fixed In v1: No
