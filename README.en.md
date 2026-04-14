# OpsPilot

[简体中文](./README.md)

> An intelligent operations assistant built on RAG and MCP

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![Milvus](https://img.shields.io/badge/Milvus-Vector%20DB-00B388.svg)](https://milvus.io/)
[![Pytest](https://img.shields.io/badge/Tested%20with-pytest-0A9EDC.svg)](https://pytest.org/)

OpsPilot is an Agent engineering project for enterprise operations scenarios. It combines intent routing, hybrid retrieval, MCP tool orchestration, and persistent workflow state to build an end-to-end troubleshooting assistant rather than a simple chat demo.

## Project Positioning

OpsPilot is best framed as:

> an engineering-oriented operations assistant prototype with clear system boundaries.

It emphasizes:

- `intent routing`
- `hybrid retrieval`
- `workflow orchestration`
- `persistent state`
- `observability`

It does not overclaim:

- a real production operations platform
- full integration with enterprise ticketing systems
- full production deployment of Prometheus / MySQL
- a multi-agent platform
- unverified efficiency or cost-saving metrics

## Core Features

- Rule-first intent routing across `smalltalk / simple_qa / knowledge_qa / aiops_diagnosis / unsupported`
- Hybrid retrieval with `Milvus + SQLite FTS5 + RRF + lightweight reranking`
- `Plan-Execute-Replan` workflow for AIOps diagnosis
- MCP-based log and monitoring tool integration
- Persistent session, message, workflow, and tool-call storage
- JWT auth with `viewer / operator / admin` role boundaries
- Lightweight metrics exposure through `/metrics`
- Key-path tests for auth, intent routing, retrieval, and API authorization

## Tech Stack

### Backend

- `FastAPI`
- `Pydantic v2`
- `Uvicorn`
- `SQLite`
- `Loguru`

### Agent / LLM / Retrieval

- `LangChain`
- `LangGraph`
- `DashScope / Qwen`
- `Milvus`
- `SQLite FTS5`
- `RRF`

### Tooling and Engineering

- `MCP`
- `FastMCP`
- `pytest`
- `pytest-cov`
- `ruff`
- `black`
- `mypy`

## Architecture

OpsPilot can be understood in five layers:

1. Frontend interaction layer
2. API access layer
3. Orchestration layer
4. Retrieval and tool layer
5. Persistence and observability layer

This makes it easier to explain the project as a coherent engineering loop instead of a collection of isolated demos.

## Quick Start

### Requirements

- Python `3.11+`
- Docker Desktop
- DashScope API key for full LLM / embedding behavior

### 1. Clone the repository

```bash
git clone https://github.com/Shuhong-BNU/OpsPilot.git
cd OpsPilot
```

### 2. Create `.env`

Copy [`.env.example`](./.env.example) to `.env` and review:

```env
APP_NAME=OpsPilot
JWT_SECRET=replace-with-a-secure-secret
DASHSCOPE_API_KEY=your-api-key
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### 3. Install dependencies

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Linux / macOS:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 4. Start the project

Windows:

```powershell
.\start-windows.bat
```

Linux / macOS:

```bash
docker compose -f vector-database.yml up -d
make start
```

### 5. Open the app

- Web UI: `http://localhost:9900`
- API docs: `http://localhost:9900/docs`
- Health check: `http://localhost:9900/health`
- Metrics: `http://localhost:9900/metrics`

### Default demo accounts

| Role | Username | Password |
|---|---|---|
| `viewer` | `viewer` | `viewer123` |
| `operator` | `operator` | `operator123` |
| `admin` | `admin` | `admin123` |

## Project Structure

```text
OpsPilot/
├── app/                    # API, services, agent logic, models, tools
├── aiops-docs/             # near-realistic operations knowledge samples
├── mcp_servers/            # MCP log and monitor services
├── static/                 # static frontend
├── tests/                  # pytest cases
├── .env.example            # environment template
├── Makefile                # Linux / macOS commands
├── start-windows.bat       # Windows start script
├── stop-windows.bat        # Windows stop script
├── vector-database.yml     # Milvus Docker Compose
└── OpsPilot_interview_handbook.md
```

## API Reference

### Auth

| Function | Method | Path | Description |
|---|---|---|---|
| Login | `POST` | `/api/auth/login` | Returns JWT and role |
| Current user | `GET` | `/api/auth/me` | Resolves login state |

### Chat and Sessions

| Function | Method | Path | Description |
|---|---|---|---|
| Chat | `POST` | `/api/chat` | Full response after intent routing |
| Streaming chat | `POST` | `/api/chat_stream` | SSE output |
| Clear session | `POST` | `/api/chat/clear` | Clears a single session |
| Session detail | `GET` | `/api/chat/session/{session_id}` | Reads message history |
| Session list | `GET` | `/api/sessions` | Lists current user sessions |
| Delete session | `DELETE` | `/api/sessions/{session_id}` | Removes a session |

### Operations Capabilities

| Function | Method | Path | Description |
|---|---|---|---|
| AIOps diagnosis | `POST` | `/api/aiops` | Streaming diagnosis, `operator/admin` only |
| Upload document | `POST` | `/api/upload` | Uploads and indexes docs |
| Index directory | `POST` | `/api/index_directory` | Batch indexing |

### Observability

| Function | Method | Path | Description |
|---|---|---|---|
| Health | `GET` | `/health` | API, Milvus, SQLite health |
| Metrics JSON | `GET` | `/metrics` | Structured metrics snapshot |
| Metrics text | `GET` | `/metrics?format=prometheus` | Prometheus text format |

## Configuration

Main configuration lives in [`.env.example`](./.env.example) and [app/config.py](./app/config.py).

### App and Service

| Variable | Description | Default |
|---|---|---|
| `APP_NAME` | project name | `OpsPilot` |
| `APP_TITLE` | UI title | `An intelligent operations assistant built on RAG and MCP` |
| `HOST` | host | `0.0.0.0` |
| `PORT` | port | `9900` |
| `DEBUG` | debug mode | `True/False` |

### Auth and Persistence

| Variable | Description | Default |
|---|---|---|
| `DATABASE_PATH` | SQLite path | `./data/opspilot.db` |
| `JWT_SECRET` | JWT signing secret | dev default |
| `JWT_EXPIRE_MINUTES` | token lifetime | `720` |
| `PASSWORD_HASH_ITERATIONS` | PBKDF2 rounds | `120000` |

### Retrieval

| Variable | Description | Default |
|---|---|---|
| `DASHSCOPE_MODEL` | chat model | `qwen-max` |
| `DASHSCOPE_EMBEDDING_MODEL` | embedding model | `text-embedding-v4` |
| `DENSE_TOP_K` | dense recall size | `6` |
| `SPARSE_TOP_K` | sparse recall size | `6` |
| `HYBRID_TOP_K` | fused candidate size | `4` |
| `RERANK_TOP_K` | reranked result size | `3` |

### MCP and Metrics

| Variable | Description | Default |
|---|---|---|
| `MCP_CLS_URL` | log query tool endpoint | `http://localhost:8003/mcp` |
| `MCP_MONITOR_URL` | monitoring tool endpoint | `http://localhost:8004/mcp` |
| `METRICS_ENABLED` | enable metrics | `True` |

## AIOps Operations Workflow

OpsPilot uses a `Plan-Execute-Replan` diagnosis loop:

1. Planner creates a diagnosis plan
2. Executor runs steps and calls MCP tools
3. Replanner decides whether to continue or converge
4. The system emits a final report and persists workflow results

This is best described as:

> an AIOps diagnosis loop driven by near-realistic operations knowledge, alert samples, and tool-assisted reasoning.

## Development Guide

### Common commands

```bash
make start
make stop
make restart
make test
make lint
make format
make coverage
```

```powershell
.\start-windows.bat
.\stop-windows.bat
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m black app tests
```

### Recommended reading order

1. [app/main.py](./app/main.py)
2. [app/services/chat_service.py](./app/services/chat_service.py)
3. [app/services/intent_service.py](./app/services/intent_service.py)
4. [app/services/retrieval_service.py](./app/services/retrieval_service.py)
5. [app/services/session_service.py](./app/services/session_service.py)
6. [app/services/auth_service.py](./app/services/auth_service.py)
7. [app/agent/mcp_client.py](./app/agent/mcp_client.py)
8. [OpsPilot_interview_handbook.md](./OpsPilot_interview_handbook.md)

## Testing and Observability

### Tests

Current tests cover:

- authentication service behavior
- rule-based intent routing
- retrieval fusion and reranking
- API authorization boundaries

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### Metrics

The project records:

- request volume
- average latency
- retrieval latency
- rerank latency
- MCP tool success/failure counts
- end-to-end AIOps workflow duration

## FAQ

### 1. What if `make` is not available on Windows?

Use:

```powershell
.\start-windows.bat
.\stop-windows.bat
```

### 2. Can the project run without a DashScope API key?

Yes, but LLM-backed answering, embeddings, and retrieval quality will degrade.

### 3. Why are upload and diagnosis endpoints restricted?

Because they are higher-risk operations. The project intentionally includes a minimal security boundary that can be explained clearly in interviews.

### 4. Is this a production system?

No. It is better described as a complete and honest engineering prototype for operations-focused agent workflows.

## Current Boundaries

### Implemented

- intent routing
- hybrid retrieval and lightweight reranking
- Plan-Execute-Replan workflow
- MCP tool integration
- persistent state
- JWT + role-based access
- lightweight metrics and key-path tests

### Partially Implemented

- reranking is lightweight, not a dedicated cross-encoder service
- monitoring, alert, and ticket data are better described as near-realistic samples

### Not Claimed

- real production integration
- multi-agent platform behavior
- production-grade permission system
- full production monitoring platform integration

## License

[MIT License](./LICENSE)
