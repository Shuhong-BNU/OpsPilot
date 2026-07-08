# OpsPilot Retrieval Evaluation

[![中文文档](https://img.shields.io/badge/文档-中文-1677ff?style=for-the-badge)](./README.md) [![English README](https://img.shields.io/badge/Docs-English-2ea44f?style=for-the-badge)](./README.en.md)

## 1. 目标

OpsPilot 提供 retrieval-only 离线评测，避免只凭现场 Demo 判断 RAG 检索质量。评测对象是当前真实 RAG retrieval stack，范围在答案生成、Groundedness、AIOps 行为、MCP 工具调用和 LLM-as-a-Judge 之前。

## 2. Evaluation Chain

```text
fixed dataset
-> retrieval_service.hybrid_search
-> Milvus dense retrieval
-> SQLite FTS5 sparse retrieval
-> RRF fusion
-> lightweight lexical-overlap rerank
-> final top3
-> Hit@3 / MRR
```

当前代码级 rerank 是 `app/services/retrieval_service.py` 中的轻量 lexical-overlap rerank。配置里存在 `DASHSCOPE_RERANK_MODEL`，但当前 retrieval path 不调用 DashScope rerank。

## 3. Dataset

数据集位于 `evals/datasets/opspilot_rag_cases.jsonl`，包含 10 条固定的项目内离线 case，来源于仓库跟踪的 5 个 `aiops-docs/*.md` 文件。

每个 case 使用 `relevant_sources` 作为评分目标。这组样例适合做项目内回归追踪，但不是通用 RAG benchmark。

## 4. Metrics

- `Hit@3`：final top 3 中至少出现一个 relevant source，则该 case 得 1；否则得 0。
- `MRR`：第一个 relevant source 的 reciprocal rank；如果未召回 relevant source，则为 0。
- Latency：runner 记录 wall-clock retrieval latency，并从 `RetrievalTrace` 中记录 dense、sparse、rerank stage latency。

## 5. Status Model

- `PASS`：完整 retrieval 链路执行成功，并且 final top 3 命中至少一个 relevant source。
- `FAIL`：完整 retrieval 链路执行成功，但 final top 3 没有命中 relevant source。这是能力结果。
- `INFRA_BLOCKED`：基础设施阻止正式 retrieval trial，例如缺少 DashScope key、Milvus 不可达、SQLite chunks 为空。这不是 capability FAIL。

## 6. Runner Modes

Measurement mode 是默认模式：

```bash
python evals/run_retrieval_eval.py
```

CI gate mode 需要显式开启：

```bash
python evals/run_retrieval_eval.py --ci
```

| Mode | Result | Report Status | Exit Code |
|---|---|---|---:|
| measurement | all PASS | PASS | 0 |
| measurement | any FAIL | FAIL | 0 |
| measurement | any INFRA_BLOCKED | INFRA_BLOCKED | 2 |
| ci | all PASS | PASS | 0 |
| ci | any FAIL | FAIL | 1 |
| ci | any INFRA_BLOCKED | INFRA_BLOCKED | 2 |

同一份 `CaseResult` 在两种模式下保持相同 capability status。`--ci` 只改变 runner mode 标记，以及 capability FAIL 时的进程退出码。

## 7. Prerequisites

正式 Hybrid Retrieval eval 需要：

- Docker / Milvus 可以通过配置的 host 和 port 访问。
- 可用且具备 embedding 权限的 `DASHSCOPE_API_KEY`。
- Milvus 和 SQLite FTS5 中已有索引后的 corpus。
- SQLite `document_chunks` 和 `document_chunks_fts` 已由 `aiops-docs/` 填充。

不要为了运行 eval 反复执行 ingestion。应先检查索引是否已存在，以及 Milvus 与 SQLite 是否一致。

## 8. Outputs

- `evals/results/`：latest raw JSONL result artifact。
- `evals/reports/`：latest Markdown report artifact。
- `evals/baselines/`：frozen historical baseline artifacts。

运行 eval 会更新 latest artifacts；frozen baselines 不应被回写。

## 9. Baseline v1

- Business Code Base: `68819d0`
- Eval Commit: `2c0db0b`
- Dataset Size: 10
- Scorable Cases: 10/10
- Hit@3: 1.000
- MRR: 0.950
- Sparse non-empty: 0/10
- Sparse relevant hit: 0/10

Baseline v1 冻结了 sparse query-builder 修复前的原始 hybrid retrieval 行为。

## 10. Diagnosis

第一版 baseline 显示 sparse path 执行了，但在固定 dataset 上没有贡献 relevant sparse hits。后续诊断确认：

- SQLite FTS5 包含 21 条真实 rows。
- SQL result mapping 正常。
- `CPU` 这类单个 ASCII token 可以命中。
- 清洗后的完整中文 query 返回 0 个 sparse hits。

Root cause classification：

```text
CHINESE_TOKENIZER_LIMITATION
+
QUERY_BUILDER_TOO_STRICT
```

## 11. AND vs OR Experiment

在同一 10-case dataset 上做了只读单变量实验，对比当前 AND-style FTS query 与 quoted-token OR matching。

| Strategy | Sparse non-empty | Sparse relevant hit |
|---|---:|---:|
| AND | 0/10 | 0/10 |
| quoted OR | 4/10 | 4/10 |

OR 策略在修改业务代码之前先通过了 modification gate。

## 12. Baseline v1.1

- Fix Commit: `61fa33e`
- Dataset Size: 10
- Scorable Cases: 10/10
- Hit@3: 1.000
- MRR: 1.000
- Sparse non-empty: 4/10
- Sparse relevant hit: 4/10

唯一业务修改是把 sparse query builder 从 multi-token AND 放宽为 quoted-token OR，同时保持 tokenizer、SQL、dense retrieval、RRF、rerank、dataset 和 metrics 不变。

## 13. Contract Follow-up

GitHub Codex Review 后续指出：retrieval miss 仍然 exit 0，这对 measurement 是正确的，但对 CI 不安全。PR #2 引入了显式 Measurement / CI Gate contract。

- Contract Commit: `2389bdd`
- Default mode: measurement
- CI mode: `--ci`

## 14. Caveats

- 10 条 cases 是项目内固定离线样例，不是通用 benchmark。
- v1 已经达到 Hit@3 ceiling，所以可见提升主要体现在 MRR 和 sparse contribution。
- latency 数字来自单次运行，不能证明因果性的 latency regression。
- 中文 tokenizer limitation 仍然存在；v1.1 只放宽 query building。
- Frozen artifacts 可能包含历史运行环境 metadata，例如本地绝对路径。它们作为历史 artifact 保留，不回写。
