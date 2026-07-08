# OpsPilot

[![中文文档](https://img.shields.io/badge/文档-中文-1677ff?style=for-the-badge)](./README.md) [![English README](https://img.shields.io/badge/Docs-English-2ea44f?style=for-the-badge)](./README.en.md)

> An intelligent operations assistant built on RAG and MCP

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![Milvus](https://img.shields.io/badge/Milvus-Vector%20DB-00B388.svg)](https://milvus.io/)
[![Pytest](https://img.shields.io/badge/Tested%20with-pytest-0A9EDC.svg)](https://pytest.org/)

OpsPilot brings conversational assistance, knowledge retrieval, AIOps diagnosis, and MCP-backed tool orchestration into one operator-facing workspace. It works well both as a runnable operations Agent example and as a demo project for retrieval, workflow orchestration, access control, and runtime visibility.

## ✨ Highlights

- 🤖 **Chat Workspace**: standard responses, streaming output, session history, and execution trace in one UI
- 🧭 **Intent Routing**: switches across `smalltalk / simple_qa / knowledge_qa / aiops_diagnosis / unsupported`
- 📚 **Hybrid Retrieval**: combines `Milvus dense recall + SQLite FTS5 sparse recall + RRF + lightweight lexical-overlap rerank`
- 📏 **Eval-driven Retrieval**: uses a fixed 10-case project-local dataset to track Hit@3, MRR, PASS / FAIL / INFRA_BLOCKED, and frozen baselines
- 🔧 **AIOps Diagnosis**: uses `Plan-Execute-Replan` to generate structured troubleshooting steps
- 🔌 **MCP Integration**: connects log and monitoring tools while persisting tool-call records
- 💾 **Persistent State**: stores sessions, messages, workflows, and tool logs in SQLite
- 🔐 **Role Boundaries**: `viewer / operator / admin` roles keep sensitive actions explicit
- 🪟 **Status Panel**: exposes model config, dependency readiness, access URLs, and service health in the frontend
- 🧪 **Critical Path Tests**: covers auth, retrieval, authorization boundaries, and system status APIs

## 🧱 Architecture Layers

- 🖥️ **Frontend**: `static/` provides the single-page workspace, streaming renderer, trace panel, and system-status panel
- 🌐 **API Layer**: `app/api/` exposes auth, chat, AIOps, upload, sessions, health, metrics, and runtime-status endpoints
- 🧠 **Service Layer**: `app/services/` implements routing, retrieval, workflow orchestration, persistence, and metrics
- 🤝 **Agent Layer**: `app/agent/` manages MCP connectivity and AIOps execution nodes
- 🧰 **Tool Layer**: `app/tools/` defines callable tools such as retrieval and time helpers
- 🗃️ **Data Layer**: SQLite stores structured state, Milvus stores vectors, and `aiops-docs/` provides demo knowledge

## 🛠️ Tech Stack

### ⚡ Quick View

- **Framework**: FastAPI + LangChain + LangGraph
- **LLM**: DashScope / Qwen
- **Retrieval**: Milvus + SQLite FTS5 + RRF + rerank
- **State Store**: SQLite
- **Tool Protocol**: MCP / FastMCP
- **Engineering**: pytest + ruff + black + mypy + Loguru

### 🧩 Detailed Stack

| Category | Technologies | Purpose |
|---|---|---|
| Web framework | FastAPI, Uvicorn, sse-starlette | REST APIs, SSE chat, streaming AIOps diagnosis |
| LLM / Agent | LangChain, LangGraph, DashScope / Qwen, langchain-qwq | chat Agent, AIOps workflow, planning, tool orchestration |
| Retrieval | Milvus, SQLite FTS5, RRF, lightweight lexical-overlap rerank | dense recall, sparse recall, fusion, and the current code-level reranker |
| Tool integration | MCP, FastMCP, langchain-mcp-adapters | log and monitoring tool integration |
| State and data | SQLite | sessions, messages, workflows, tool logs, document chunks |
| Engineering | pytest, pytest-cov, ruff, black, mypy, Loguru | testing, linting, formatting, logging |

## 📏 Retrieval Eval Baseline

OpsPilot now includes a retrieval-only offline eval path over the real `hybrid_search` stack:

```text
fixed dataset -> Milvus dense -> SQLite FTS5 sparse -> RRF -> lightweight rerank -> final top3
```

This is a fixed project-local 10-case eval, not a general benchmark.

| Metric | Baseline v1 | Baseline v1.1 |
|---|---:|---:|
| Scorable | 10/10 | 10/10 |
| Hit@3 | 1.000 | 1.000 |
| MRR | 0.950 | 1.000 |
| Sparse non-empty | 0/10 | 4/10 |
| Sparse relevant hit | 0/10 | 4/10 |

The engineering path was: Baseline v1 showed sparse contribution at 0/10; trace and FTS5 checks identified Chinese tokenizer limits plus overly strict multi-token AND matching; a read-only AND vs quoted OR experiment justified one minimal sparse query-builder fix; Baseline v1.1 then improved MRR on the fixed project-local dataset.

The eval runner defaults to Measurement mode: capability FAIL is recorded in the report while the process exits 0. `--ci` enables gate behavior: capability FAIL exits 1, while INFRA_BLOCKED always exits 2. See [evals/README.md](./evals/README.md).

## 🚀 Quick Start

### 🧰 Requirements

- Python `3.11+`
- Docker Desktop
- DashScope API key when you want real model and embedding behavior

### 🐧 Linux / macOS

```bash
git clone https://github.com/Shuhong-BNU/OpsPilot.git
cd OpsPilot

cp .env.example .env

python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

docker compose -f vector-database.yml up -d
make start
```

### 🪟 Windows PowerShell

```powershell
git clone https://github.com/Shuhong-BNU/OpsPilot.git
cd OpsPilot

Copy-Item .env.example .env
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

.\start-windows.bat
```

Manual startup:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

docker compose -f vector-database.yml up -d
.\.venv\Scripts\python.exe mcp_servers\cls_server.py
.\.venv\Scripts\python.exe mcp_servers\monitor_server.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 9900
```

## 🔐 Demo Accounts

| Role | Username | Password |
|---|---|---|
| `viewer` | `viewer` | `viewer123` |
| `operator` | `operator` | `operator123` |
| `admin` | `admin` | `admin123` |

## 🌐 Access Points

- **Web UI**: `http://localhost:9900`
- **API Docs**: `http://localhost:9900/docs`
- **Health Check**: `http://localhost:9900/health`
- **Metrics**: `http://localhost:9900/metrics`
- **System Status API**: `GET /api/system/status`

## 📡 API Overview

| Function | Method | Path | Description |
|---|---|---|---|
| Login | `POST` | `/api/auth/login` | returns JWT and role |
| Current user | `GET` | `/api/auth/me` | resolves login state |
| Chat | `POST` | `/api/chat` | returns a full response after intent routing |
| Streaming chat | `POST` | `/api/chat_stream` | SSE output with route / content / done |
| Clear session | `POST` | `/api/chat/clear` | clears one session |
| Session detail | `GET` | `/api/chat/session/{session_id}` | returns message history |
| Session list | `GET` | `/api/sessions` | lists all sessions for the current user |
| Session detail | `GET` | `/api/sessions/{session_id}` | returns one session and its message history |
| Delete session | `DELETE` | `/api/sessions/{session_id}` | deletes one session |
| AIOps diagnosis | `POST` | `/api/aiops` | streaming diagnosis for `operator/admin` |
| Upload document | `POST` | `/api/upload` | `operator/admin`; uploads and indexes a document |
| Batch index | `POST` | `/api/index_directory` | `operator/admin`; indexes a directory |
| System status | `GET` | `/api/system/status` | returns model, dependency, and access status |
| Health check | `GET` | `/health` | checks API / Milvus / SQLite |
| Metrics snapshot | `GET` | `/metrics` | returns JSON metrics; `?format=prometheus` returns Prometheus-format text |

## 🗂️ Project Structure

### 🧭 Directory Roles

- `app/`: application core, including APIs, services, Agent modules, models, and tools
- `aiops-docs/`: operations knowledge samples for retrieval and diagnosis demos
- `mcp_servers/`: MCP servers for log and monitoring access
- `static/`: single-page frontend workspace
- `tests/`: service, API, frontend-security, streaming-timing, and Eval Contract tests
- `evals/`: Retrieval Eval dataset, runner, latest results/report, and frozen baselines
- `docs/assets/`: screenshot assets and screenshot maintenance notes
- `data/`, `logs/`, `uploads/`, `volumes/`: runtime data, logs, uploaded files, and container volumes

### 🧩 File-by-File Map

```text
OpsPilot/
├── app/                                      # Application core
│   ├── __init__.py                           # Package init
│   ├── main.py                               # FastAPI entrypoint, routes, static mount
│   ├── config.py                             # app, model, retrieval, MCP, and metrics config
│   ├── api/                                  # HTTP API layer
│   │   ├── __init__.py                       # API package init
│   │   ├── auth.py                           # login and current-user endpoints
│   │   ├── chat.py                           # chat and streaming endpoints
│   │   ├── aiops.py                          # streaming AIOps endpoint
│   │   ├── file.py                           # upload and directory indexing endpoints
│   │   ├── health.py                         # health-check endpoint
│   │   ├── metrics.py                        # JSON / Prometheus metrics endpoint
│   │   ├── sessions.py                       # session list, detail, delete endpoints
│   │   ├── system.py                         # runtime status and dependency readiness endpoint
│   │   └── dependencies.py                   # auth and role-based dependencies
│   ├── services/                             # Business services
│   │   ├── __init__.py                       # service package init
│   │   ├── auth_service.py                   # default accounts, password validation, JWT
│   │   ├── chat_service.py                   # chat entry and route dispatch
│   │   ├── intent_service.py                 # intent routing and fallback classification
│   │   ├── rag_agent_service.py              # RAG Agent and tool orchestration
│   │   ├── aiops_service.py                  # AIOps workflow orchestration
│   │   ├── retrieval_service.py              # hybrid retrieval, RRF, rerank, trace recording
│   │   ├── session_service.py                # session, message, and workflow persistence
│   │   ├── database_service.py               # SQLite setup, queries, FTS5 retrieval
│   │   ├── metrics_service.py                # runtime metrics collection
│   │   ├── runtime_status_service.py         # runtime status, model config, dependency aggregation
│   │   ├── request_context_service.py        # request-context helpers
│   │   ├── vector_store_manager.py           # Milvus VectorStore wrapper
│   │   ├── vector_embedding_service.py       # DashScope embedding wrapper
│   │   ├── vector_index_service.py           # file reading, chunking, indexing
│   │   ├── vector_search_service.py          # vector search logic
│   │   └── document_splitter_service.py      # Markdown / text splitting
│   ├── agent/                                # Agent coordination layer
│   │   ├── __init__.py                       # Agent package init
│   │   ├── mcp_client.py                     # MultiServer MCP client
│   │   └── aiops/                            # AIOps workflow nodes
│   │       ├── __init__.py                   # AIOps node package init
│   │       ├── planner.py                    # planning node
│   │       ├── executor.py                   # tool execution node
│   │       ├── replanner.py                  # replanning node
│   │       ├── state.py                      # workflow state definition
│   │       └── utils.py                      # helper utilities
│   ├── models/                               # Pydantic models
│   │   ├── __init__.py                       # model package init
│   │   ├── auth.py                           # auth request and response models
│   │   ├── request.py                        # chat and clear request models
│   │   ├── response.py                       # common response models
│   │   ├── aiops.py                          # AIOps request and response models
│   │   ├── session.py                        # session response models
│   │   └── document.py                       # document indexing models
│   ├── tools/                                # callable Agent tools
│   │   ├── __init__.py                       # tool package init
│   │   ├── knowledge_tool.py                 # retrieval tool
│   │   └── time_tool.py                      # time helper
│   ├── core/                                 # low-level wrappers
│   │   ├── __init__.py                       # core package init
│   │   ├── llm_factory.py                    # LLM factory
│   │   └── milvus_client.py                  # Milvus connection and collection manager
│   └── utils/                                # shared utilities
│       ├── __init__.py                       # utils package init
│       └── logger.py                         # Loguru logger setup
├── aiops-docs/                               # Operations knowledge samples
│   ├── cpu_high_usage.md                     # CPU troubleshooting sample
│   ├── disk_high_usage.md                    # Disk troubleshooting sample
│   ├── memory_high_usage.md                  # Memory troubleshooting sample
│   ├── service_unavailable.md                # Service-unavailable sample
│   └── slow_response.md                      # Slow-response sample
├── evals/                                    # Retrieval Eval
│   ├── README.md                             # eval purpose, metrics, modes, and baselines
│   ├── datasets/opspilot_rag_cases.jsonl     # fixed 10-case project-local dataset
│   ├── run_retrieval_eval.py                 # Measurement / --ci runner
│   ├── results/                              # latest raw results
│   ├── reports/                              # latest Markdown report
│   └── baselines/                            # frozen v1 / v1.1 artifacts
├── mcp_servers/                              # MCP services
│   ├── cls_server.py                         # log query MCP server
│   ├── monitor_server.py                     # monitoring MCP server
│   └── README.md                             # MCP service notes
├── static/                                   # Frontend workspace
│   ├── index.html                            # page structure
│   ├── app.js                                # interaction logic, trace, and status UI
│   └── styles.css                            # styles
├── tests/                                    # Automated tests
│   ├── conftest.py                           # fixtures and shared setup
│   ├── test_api_security.py                  # API authorization boundary tests
│   ├── test_auth_service.py                  # auth service tests
│   ├── test_intent_service.py                # intent routing tests
│   ├── test_retrieval_service.py             # retrieval, RRF, query-builder, and rerank tests
│   ├── test_retrieval_eval_contract.py        # Eval Measurement / --ci contract tests
│   ├── test_chat_stream_timing.py             # streaming timing tests
│   ├── test_frontend_security.py              # frontend security-boundary tests
│   ├── test_session_api.py                    # session API tests
│   └── test_system_status_api.py              # system status API tests
├── docs/                                     # Supporting docs and assets
│   └── assets/                               # screenshot assets and conventions
│       ├── README.md                         # capture rules, naming, and checklist
│       └── screenshots/                      # README screenshot directory
├── data/                                     # runtime SQLite data
├── logs/                                     # runtime logs
├── uploads/                                  # uploaded file cache
├── volumes/                                  # Milvus-related container volumes
├── .env.example                              # environment template
├── Makefile                                  # Linux / macOS shortcuts
├── OpsPilot_demo_script.md                   # demo walkthrough
├── OpsPilot_interview_handbook.md            # interview and project talking points
├── pyproject.toml                            # dependencies and tooling config
├── pyrightconfig.json                        # Pyright config
├── start-windows.bat                         # Windows startup script
├── stop-windows.bat                          # Windows shutdown script
├── vector-database.yml                       # Milvus Docker Compose
├── README.md                                 # Chinese README
└── README.en.md                              # English README
```

## 📚 Documentation Index

- [OpsPilot_demo_script.md](./OpsPilot_demo_script.md): demo flow, prompts, and speaking sequence
- [OpsPilot_interview_handbook.md](./OpsPilot_interview_handbook.md): interview narrative, eval-driven engineering story, and Q&A prep
- [evals/README.md](./evals/README.md): Retrieval Eval, Baseline v1/v1.1, and Measurement / --ci Contract
- [mcp_servers/README.md](./mcp_servers/README.md): MCP service notes
- [docs/assets/README.md](./docs/assets/README.md): screenshot asset maintenance guide

## ⚙️ Key Configuration

### 🧪 App and Model Settings

| Variable | Description | Default |
|---|---|---|
| `APP_NAME` | application name | `OpsPilot` |
| `APP_TITLE` | page title | `An intelligent operations assistant built on RAG and MCP` |
| `DASHSCOPE_API_KEY` | DashScope API key | empty |
| `DASHSCOPE_MODEL` | primary chat model | `qwen-max` |
| `DASHSCOPE_EMBEDDING_MODEL` | embedding model | `text-embedding-v4` |
| `DASHSCOPE_RERANK_MODEL` | rerank model | `qwen3-rerank` |

### 🗃️ Storage and Retrieval

| Variable | Description | Default |
|---|---|---|
| `DATABASE_PATH` | SQLite database path | `./data/opspilot.db` |
| `MILVUS_HOST` | Milvus host | `localhost` |
| `MILVUS_PORT` | Milvus port | `19530` |
| `RAG_TOP_K` | final reference count | `3` |
| `DENSE_TOP_K` | dense recall candidates | `6` |
| `SPARSE_TOP_K` | sparse recall candidates | `6` |
| `HYBRID_TOP_K` | post-fusion count | `4` |
| `RERANK_TOP_K` | post-rerank count | `3` |

### 🔐 Auth and Runtime

| Variable | Description | Default |
|---|---|---|
| `JWT_SECRET` | JWT signing secret | development default |
| `JWT_EXPIRE_MINUTES` | JWT lifetime | `720` |
| `PASSWORD_HASH_ITERATIONS` | PBKDF2 iterations | `120000` |
| `MCP_CLS_URL` | CLS MCP endpoint | `http://localhost:8003/mcp` |
| `MCP_MONITOR_URL` | Monitor MCP endpoint | `http://localhost:8004/mcp` |
| `METRICS_ENABLED` | enables metrics collection | `True` |


## 🔌 MCP Mock / Real Boundary

The MCP protocol path is real: OpsPilot uses `MultiServerMCPClient` to connect two local FastMCP servers, and AIOps workflows persist tool-call records.

The default log and monitoring data sources in this repository are reproducible mock data. The project does not ship with production Prometheus, real Tencent CLS, or MySQL integration enabled by default. `mcp_servers/` keeps the integration points where real data-source adapters can be added later.

## 🎯 AIOps Workflow

1. **Planner** creates the diagnostic plan
2. **Executor** runs MCP-backed steps
3. **Replanner** decides whether to continue, revise, or stop
4. **Reporter** summarizes the result and writes into `workflow_runs`

Typical demo scenarios:

- CPU, memory, and disk alerts
- service-unavailable and slow-response troubleshooting
- diagnosis that combines logs, monitoring data, and runbook knowledge

## 🎬 Demo and Recording

- Use `viewer` for standard chat, retrieval answers, and streaming replies
- Use `operator` for AIOps diagnosis, document upload, and system-status demos
- Capture the main workspace for answers and the left panel for session history, trace, and runtime status
- Recording notes and screenshot rules live in [OpsPilot_demo_script.md](./OpsPilot_demo_script.md) and [docs/assets/README.md](./docs/assets/README.md)

## 🧪 Testing and Observability

### ✅ Current Coverage

- auth service tests
- intent routing tests
- hybrid retrieval, RRF, query-builder, and rerank tests
- Retrieval Eval Measurement / `--ci` Contract tests
- streaming chat timing tests
- API and frontend authorization-boundary tests
- session API and system status API tests

The repository has local testing and quality tooling configured. GitHub CI is not currently configured, so this README intentionally does not include a CI badge.

### ▶️ Run Tests

```bash
make test
make coverage
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

### 📈 Metrics

- total HTTP requests
- average request latency
- dense retrieval latency
- sparse retrieval latency
- rerank latency
- MCP tool-call success / failure rates
- total AIOps workflow duration

## 🧭 Development Commands

### 🐧 Linux / macOS

```bash
make init
make start
make stop
make restart

make install-dev
make sync

make up
make down
make status

make upload
make list-docs
make check
make status-mcp

make format
make lint
make fix
make test
make coverage
```

### 🪟 Windows

```powershell
.\start-windows.bat
.\stop-windows.bat
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m black app tests
```

## ❓ FAQ

### 🪟 What if `make` is unavailable on Windows?

Use:

```powershell
.\start-windows.bat
.\stop-windows.bat
```

### 🔑 Can the project run without a DashScope API key?

The UI, FastAPI service, and local unit tests can run, but full model and retrieval behavior cannot.

| Capability | Without DashScope Key |
|---|---|
| UI / FastAPI | Starts |
| Local unit tests | Can run |
| Real LLM chat | Not available; returns missing-key guidance or lightweight fallback |
| Embedding | Not available |
| Dense indexing | Not available |
| Full Hybrid Retrieval | Not formally available |
| Retrieval Eval | Marked `INFRA_BLOCKED` |

Sparse search depends on whether a local SQLite sparse index already exists, so it should not be treated as full Hybrid Retrieval availability. Configure `DASHSCOPE_API_KEY` for a full demo.

### 🐳 What should I do if `/health` reports Milvus errors?

Make sure Docker Desktop is running, then execute:

```bash
docker compose -f vector-database.yml up -d
```

### 📤 Why does document upload fail?

Typical causes:

- the current account is not `operator/admin`
- the request does not include `Authorization: Bearer <token>`

### 🧪 Is this a production system?

Not yet. It is better positioned as a complete, clearly bounded, engineering-focused operations Agent example and demo project.
