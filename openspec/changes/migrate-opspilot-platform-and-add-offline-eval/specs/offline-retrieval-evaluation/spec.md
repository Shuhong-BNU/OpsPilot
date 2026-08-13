## ADDED Requirements

### Requirement: Deterministic offline retrieval regression evaluation
OpsPilot SHALL provide a versioned retrieval-only evaluation that runs without Milvus, remote model credentials, or network access while exercising the production retrieval orchestration path.

#### Scenario: Fixed dataset runs against tracked corpus

- **WHEN** a developer runs `evals/run_retrieval_eval.py`
- **THEN** the runner MUST load the versioned JSONL dataset and tracked Markdown corpus, and MUST fail when a relevant source is absent from the corpus.

#### Scenario: Production retrieval orchestration is exercised

- **WHEN** an offline evaluation case is executed
- **THEN** it MUST execute `KnowledgeRetrievalTool` scope filtering, BM25L, RRF fusion, rerank result shaping, citations, and stage-rank evidence while replacing only Milvus, embedding, and remote rerank boundaries with deterministic adapters.

#### Scenario: Metrics and evidence are emitted

- **WHEN** an evaluation run completes
- **THEN** it MUST write per-case Hit@1, Hit@3, MRR, Recall@3, ranked sources, and vector/BM25/RRF/rerank evidence to JSONL and a Markdown report.

#### Scenario: Offline result boundary is clear

- **WHEN** the report is generated
- **THEN** it MUST state that the result is not a quality, latency, or cost claim for the production Milvus/Qwen deployment.
