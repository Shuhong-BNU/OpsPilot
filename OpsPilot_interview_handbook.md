# OpsPilot Interview Handbook

这份手册用于面试和项目讲解。它不替代 README，也不把项目包装成生产平台；重点是讲清楚 OpsPilot 的工程闭环。

## 1. 30 秒项目介绍

OpsPilot 是一个基于 RAG 与 MCP 的智能运维助手。我把普通问答、知识库检索、AIOps 诊断、权限控制、SQLite 状态持久化和本地 MCP 工具链整合到一个可运行的 FastAPI + 前端工作台里。项目最有价值的一点不是“能跑 Demo”，而是我为 RAG 检索链路建立了固定离线评测，基于真实 trace 找到 sparse retrieval 没有贡献的问题，并通过单变量实验做了最小修复。

## 2. 3 分钟项目介绍

OpsPilot 面向运维场景，核心入口是一个聊天工作台。用户问题先经过意图识别，再进入 smalltalk、simple QA、knowledge QA、AIOps diagnosis 或 unsupported。knowledge QA 走 RAG 链路：Milvus dense retrieval、SQLite FTS5 sparse retrieval、RRF 融合和当前代码中的轻量 lexical-overlap rerank。AIOps 链路使用 Plan-Execute-Replan，把问题拆成步骤，并通过 MCP Client 调用本地日志和监控工具。

工程上，我做了三件事。第一，补齐可运行链路：FastAPI、SQLite、Milvus、DashScope、MCP server、前端状态面板和角色权限。第二，建立 retrieval-only Eval Harness，用固定 10 条项目内样例评估真实 `hybrid_search`，记录 Hit@3、MRR、stage latency、PASS / FAIL / INFRA_BLOCKED。第三，通过 Baseline v1 发现 sparse 贡献为 0/10，定位 FTS5 中文 tokenizer 限制和 strict AND 查询过严，再通过 AND vs quoted OR 单变量实验，把 sparse relevant hit 从 0/10 提升到 4/10，并在项目内固定样例上把 MRR 从 0.95 提升到 1.00。

## 3. 项目为什么不是普通 RAG Demo

普通 RAG Demo 往往只展示“问一个问题，模型答出来”。OpsPilot 的重点是：

- 有真实 retrieval trace，而不是只看最终回答。
- 有固定 dataset 和 frozen baselines。
- 区分能力 FAIL 与 INFRA_BLOCKED。
- 用单变量实验解释为什么改 query builder。
- 用 PR #2 明确 Measurement runner 和 CI gate 的退出码 contract。

## 4. 最强工程故事

```text
Eval Harness
-> Baseline v1
-> 发现 Sparse 0/10
-> FTS5 中文 tokenizer + strict AND 根因定位
-> AND vs quoted OR 单变量实验
-> Minimal Query Builder Fix
-> Baseline v1.1
-> Codex Review 指出 exit-code ambiguity
-> Measurement / CI Gate Contract
```

讲法：我没有先调参，而是先固定评测集和指标。Baseline v1 的 Hit@3 已经是 1.0，但 MRR 还有空间，而且 trace 显示 sparse retrieval 没有实际贡献。这说明“表面 Hybrid，实际主要靠 Dense”。我继续诊断 SQLite FTS5，确认数据存在、mapping 正常、单 token 能命中，但中文长 query 和 AND 组合过严。于是先做只读 AND vs OR 实验，看到 OR 能让 sparse relevant hit 从 0/10 到 4/10，才做最小 query-builder 修复。

## 5. 代码位置地图

| Story | File |
|---|---|
| Hybrid retrieval | `app/services/retrieval_service.py` |
| SQLite FTS5 sparse query | `app/services/database_service.py` |
| Document ingestion | `app/services/vector_index_service.py` |
| Embedding wrapper | `app/services/vector_embedding_service.py` |
| Milvus vector store | `app/services/vector_store_manager.py` |
| Eval runner | `evals/run_retrieval_eval.py` |
| Dataset | `evals/datasets/opspilot_rag_cases.jsonl` |
| Baseline v1 | `evals/baselines/v1/` |
| Baseline v1.1 | `evals/baselines/v1.1/` |
| Eval contract tests | `tests/test_retrieval_eval_contract.py` |
| MCP client | `app/agent/mcp_client.py` |
| MCP servers | `mcp_servers/` |

## 6. 高频面试问题

### 为什么做 Eval？

30 秒答案：因为 RAG 很容易只看 Demo 成功，不知道检索链路到底哪一段在贡献。我做固定 10-case eval，把 retrieval 变成可重复测量的工程对象。

深入追问方向：dataset schema、Hit@3、MRR、trace、latency、frozen baseline。

边界：这不是通用 benchmark，只是项目内固定样例。

### Hit@3 与 MRR 区别？

30 秒答案：Hit@3 只看 Top 3 是否命中任意 relevant source；MRR 看第一个 relevant source 的排名，越靠前分数越高。

深入追问方向：为什么 v1 Hit@3 已经 1.0，但 MRR 仍能提升。

边界：不要把 Hit@3 叫严格 Recall@3。

### 为什么 INFRA_BLOCKED 不算 FAIL？

30 秒答案：FAIL 是完整链路跑完但能力没命中；INFRA_BLOCKED 是 Milvus、Embedding、SQLite 等基础设施没跑起来。它们代表不同问题，混在一起会污染能力指标。

深入追问方向：exit code 2、CI gate、DashScope key restrictions。

边界：INFRA_BLOCKED 不参与能力分。

### 为什么 v1 Hit@3 已经 1.0 还继续查？

30 秒答案：因为 trace 显示 sparse retrieval 没贡献，系统名义上是 Hybrid，但实际像 Dense-only。Hit@3 到顶不代表链路健康。

深入追问方向：MRR、sparse relevant hit、diagnostic value of trace。

边界：v1 不是坏 baseline，它是能力起点。

### 为什么 Hybrid 实际不 Hybrid？

30 秒答案：dense 有召回，sparse 查询执行但中文 query 基本 0 hit，所以 fusion 阶段缺少 sparse 贡献。

深入追问方向：SQLite FTS5 tokenizer、AND query、mapping check。

边界：不是 FTS 表为空，也不是 mapping 丢结果。

### 为什么不直接换中文 tokenizer？

30 秒答案：换 tokenizer 会改变 schema、索引和 corpus，需要重建索引，变量太大。我先做最小 query-builder 修复，保留现有 FTS5 schema。

深入追问方向：单变量实验、风险控制、评测可比性。

边界：中文 tokenizer limitation 仍然存在。

### 为什么做单变量实验？

30 秒答案：为了证明 OR 策略本身有效，而不是通过重建索引、换模型或调 top_k 混出结果。

深入追问方向：AND 0/10，quoted OR 4/10。

边界：单变量实验只证明当前 dataset 上有效。

### 为什么 OR 而不是 AND？

30 秒答案：当前 TOKEN_PATTERN 对中文切分有限，多 token AND 要求过严，导致中文问题几乎不命中。quoted OR 放宽匹配，能恢复部分 sparse contribution。

深入追问方向：FTS5 MATCH syntax、安全 quoting。

边界：不是召回越多越好，后续仍需更强中文分词。

### 为什么不回写 Baseline？

30 秒答案：baseline 是历史证据，回写会破坏可复现链路。新行为应该通过新 baseline 或新 report 体现。

深入追问方向：artifact fingerprint、commit mapping。

边界：历史 artifact 可能包含运行环境 metadata。

### Measurement 和 CI Gate 为什么分开？

30 秒答案：Measurement 要完整记录能力 FAIL，所以 fully executed 即可 exit 0；CI gate 要阻止 regression，所以 FAIL 应 exit 1。

深入追问方向：`--ci`、exit code 1/2、report status。

边界：`--ci` 不改变 case status 或 metrics。

### 为什么用 Merge Commit？

30 秒答案：PR #1 的两个 commit 是 Eval -> Fix 的因果链，保留原 SHA 能清楚展示工程迭代历史。

深入追问方向：baseline v1 commit、v1.1 fix commit。

边界：不是所有 PR 都必须 merge commit。

### MCP 哪些是真，哪些是 Mock？

30 秒答案：MCP client、FastMCP server、tool 调用链是真；默认日志和监控数据源是 mock，没有接生产 Prometheus 或真实腾讯云 CLS。

深入追问方向：`mcp_servers/`, `app/agent/mcp_client.py`。

边界：不要说已接生产监控。

### 这个项目的边界是什么？

30 秒答案：它是智能运维 Agent 工程样例，不是生产平台；Eval 是项目内固定样例，不是通用 benchmark；MCP 数据源默认 mock。

深入追问方向：可扩展点、未来 PR。

边界：不要夸大生产可用性。

## 7. 简历安全表述

构建 Milvus Dense + SQLite FTS5 Sparse 混合检索链路，并设计固定 Retrieval Eval 对 RRF / rerank 全链路进行离线评测；通过 trace 定位中文 Sparse 查询失效问题，以单变量实验将 Sparse relevant hit 从 0/10 提升至 4/10，在项目内 10 条固定样例上将 MRR 从 0.95 提升至 1.00。

## 8. 不可夸大事项

- MCP 数据源当前默认 Mock。
- 不是生产 Prometheus。
- 不是生产 CLS。
- 不是通用 benchmark。
- latency 没有得到因果结论。
- tokenizer limitation 仍存在。
- Baseline v1 / v1.1 是项目内固定样例的历史结果。
