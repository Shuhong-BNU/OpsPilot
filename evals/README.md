# OpsPilot Retrieval Evaluation

## 1. Purpose

OpsPilot includes a retrieval-only eval so retrieval quality is not judged only by live demos. The eval measures the current RAG retrieval stack before answer generation, groundedness, AIOps behavior, MCP tool calls, or LLM-as-a-Judge.

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

The current code-level reranker is a lightweight lexical-overlap rerank step in `app/services/retrieval_service.py`. The config contains `DASHSCOPE_RERANK_MODEL`, but the current retrieval path does not call DashScope rerank.

## 3. Dataset

The dataset lives at `evals/datasets/opspilot_rag_cases.jsonl`. It contains 10 fixed project-local offline cases derived from the five tracked `aiops-docs/*.md` files.

Each case uses `relevant_sources` as the scoring target. These cases are useful for local regression tracking, but they are not a general RAG benchmark.

## 4. Metrics

- `Hit@3`: a case scores 1 when at least one relevant source appears in the final top 3; otherwise it scores 0.
- `MRR`: reciprocal rank of the first relevant source; 0 when no relevant source is retrieved.
- Latency: the runner records wall-clock retrieval latency plus dense, sparse, and rerank stage latency from `RetrievalTrace`.

## 5. Status Model

- `PASS`: full retrieval chain executed and at least one relevant source hit the final top 3.
- `FAIL`: full retrieval chain executed, but the final top 3 missed the relevant source. This is a capability result.
- `INFRA_BLOCKED`: infrastructure prevented a formal retrieval trial, such as missing DashScope key, unreachable Milvus, or empty SQLite chunks. This is not a capability FAIL.

## 6. Runner Modes

Measurement mode is the default:

```bash
python evals/run_retrieval_eval.py
```

CI gate mode is explicit:

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

The same `CaseResult` data keeps the same capability status in both modes. `--ci` only changes the runner mode label and the process exit code for capability FAIL.

## 7. Prerequisites

A formal Hybrid Retrieval eval requires:

- Docker / Milvus reachable at the configured host and port.
- A real `DASHSCOPE_API_KEY` with embedding access.
- Existing indexed corpus in Milvus and SQLite FTS5.
- SQLite `document_chunks` and `document_chunks_fts` populated from `aiops-docs/`.

Do not repeatedly run ingestion just to run the eval. First inspect whether indexes already exist and whether Milvus and SQLite are consistent.

## 8. Outputs

- `evals/results/`: latest raw JSONL result artifact.
- `evals/reports/`: latest Markdown report artifact.
- `evals/baselines/`: frozen historical baseline artifacts.

Latest artifacts are allowed to change when the eval is run. Frozen baselines should not be rewritten.

## 9. Baseline v1

- Business Code Base: `68819d0`
- Eval Commit: `2c0db0b`
- Dataset Size: 10
- Scorable Cases: 10/10
- Hit@3: 1.000
- MRR: 0.950
- Sparse non-empty: 0/10
- Sparse relevant hit: 0/10

Baseline v1 froze the original hybrid retrieval behavior before the sparse query-builder fix.

## 10. Diagnosis

The first baseline showed that the sparse path executed but did not contribute relevant sparse hits on the fixed dataset. Follow-up diagnosis confirmed:

- SQLite FTS5 contained 21 real rows.
- SQL result mapping worked.
- Single ASCII token queries such as `CPU` could match.
- Full cleaned Chinese queries returned zero sparse hits.

Root cause classification:

```text
CHINESE_TOKENIZER_LIMITATION
+
QUERY_BUILDER_TOO_STRICT
```

## 11. AND vs OR Experiment

A read-only single-variable experiment compared the current AND-style FTS query with quoted-token OR matching on the same 10 cases.

| Strategy | Sparse non-empty | Sparse relevant hit |
|---|---:|---:|
| AND | 0/10 | 0/10 |
| quoted OR | 4/10 | 4/10 |

The OR strategy passed the modification gate before business code changed.

## 12. Baseline v1.1

- Fix Commit: `61fa33e`
- Dataset Size: 10
- Scorable Cases: 10/10
- Hit@3: 1.000
- MRR: 1.000
- Sparse non-empty: 4/10
- Sparse relevant hit: 4/10

The only business change was relaxing the sparse query builder from multi-token AND to quoted-token OR while keeping the existing tokenizer, SQL, dense retrieval, RRF, rerank, dataset, and metrics unchanged.

## 13. Contract Follow-up

A GitHub Codex Review later pointed out that retrieval misses would still exit 0, which is correct for measurement but unsafe for CI. PR #2 introduced the explicit Measurement / CI Gate contract.

- Contract Commit: `2389bdd`
- Default mode: measurement
- CI mode: `--ci`

## 14. Caveats

- The 10 cases are fixed project-local offline samples, not a general benchmark.
- v1 already reached Hit@3 ceiling, so the visible improvement is MRR and sparse contribution.
- The latency numbers are from single runs; they do not prove a causal latency regression.
- Chinese tokenizer limitations still exist; the v1.1 fix only relaxes query building.
- Frozen artifacts may contain historical runtime metadata such as absolute local paths. They are preserved as historical artifacts and are not rewritten.
