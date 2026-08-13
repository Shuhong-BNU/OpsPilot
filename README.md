# OpsPilot

[![中文文档](https://img.shields.io/badge/Docs-%E4%B8%AD%E6%96%87-1677ff?style=for-the-badge)](./README.md)

> 基于 RAG、Agent、LangGraph 与 MCP 的本地优先 AIOps 工作台。

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3-42b883.svg)](https://vuejs.org/)
[![Milvus](https://img.shields.io/badge/Milvus-Vector%20DB-00B388.svg)](https://milvus.io/)

OpsPilot 将流式 Agent 对话、受权限控制的知识检索、真实日志 MCP、告警驱动诊断和可追溯报告整合为一个可本机运行的运维工作台。项目的目标是让一次诊断从告警、检索、工具调用到结论都保留可检查的证据。

## 核心能力

- **Agent 对话**：基于 LangChain `create_agent`、Qwen 与 SSE 的流式对话；支持会话、Prompt、Skill、记忆压缩、引用和反馈。
- **权限化 RAG**：Milvus 向量召回、BM25L、RRF 融合与 Qwen rerank；知识库、文档、向量和引用均受当前用户与 tenant 范围约束。
- **AIOps 诊断**：LangGraph `Plan -> Execute -> Replan -> Report` 图编排，支持从活动告警建立持久化诊断任务，输出步骤、证据和 Markdown 报告。
- **真实 MCP 工具**：通过腾讯云官方 CLS MCP Server 查询真实日志；支持用户级 MCP 连接配置、连通性检查、重试、超时、同名工具保护与调用审计。
- **可恢复运行时**：SQLite durable job runtime 管理诊断和索引任务的租约、心跳、重试、超时、取消和重启恢复。
- **前后端契约**：HTTP、错误码、OpenAPI 与 SSE 类型集中在共享 TypeScript contracts，避免前后端接口漂移。
- **离线检索 Eval v2**：用固定题集验证生产检索编排的回归行为，并输出每个候选在 vector、BM25、RRF 与 rerank 阶段的排序证据。

## 架构

```text
Vue 3 workspace
       |
       | typed HTTP / SSE contracts
       v
FastAPI application
  |        |             |
  |        |             +-- LangChain Agent + MCP tools
  |        +-- LangGraph AIOps diagnosis
  +-- KnowledgeRetrievalTool
          |             |
          |             +-- BM25L -> RRF -> Qwen rerank
          +-- Milvus vector search

SQLite: user-scoped business data, jobs, audits, evidence
Milvus: user-scoped document vectors
CLS MCP: real cloud log tools
```

## 技术栈

| 领域 | 实现 | 作用 |
| --- | --- | --- |
| 前端 | Vue 3、Vite、TypeScript、Pinia | 响应式工作台、状态管理与 SSE 展示 |
| 后端 | Python、FastAPI、Pydantic v2、SQLAlchemy、Alembic | API、认证、持久化与后台任务 |
| Agent | LangChain、LangGraph、OpenAI-compatible Qwen | 工具调用、对话与诊断编排 |
| 检索 | Milvus、BM25L、RRF、Qwen rerank | 混合召回、融合、精排与引用证据 |
| 集成 | 腾讯云 CLS MCP Server、Prometheus、Alertmanager | 真实日志、指标与活动告警 |
| 工程质量 | uv、pytest、Ruff、Pyright、Vitest | 依赖管理、测试与静态检查 |

## 离线 Retrieval Eval v2

Eval v2 是新版 OpsPilot 的确定性检索回归评测，不调用任何 AI API。它使用 5 份项目内 SOP 语料和 10 道预先标注正确来源的问题，复用生产 `KnowledgeRetrievalTool` 的权限过滤、BM25L、RRF、结果组装和阶段证据逻辑。

为了能在没有网络、Milvus、Qwen API Key 的环境稳定复现，只有外部边界替换为确定性本地 adapter：内存向量库、token-hash embedding 与 token-overlap rerank。它验证的是检索编排没有回归，不代表线上 Qwen 或 Milvus 的质量、延迟和成本。

| 指标 | 含义 |
| --- | --- |
| Hit@1 | 第 1 条结果是否为预标注相关来源 |
| Hit@3 | 前 3 条结果是否至少包含一个相关来源 |
| MRR | 第一个相关来源排名的倒数 |
| Recall@3 | 前 3 条找回的相关来源占全部标注来源的比例 |

执行：

```bash
cd apps/backend
uv run python ../../evals/run_retrieval_eval.py
```

输入和输出分别位于 `evals/datasets/`、`evals/corpus/`、`evals/results/`、`evals/reports/`；迁移前旧实现的 v1/v1.1 结果保存在 `evals/baselines/`，仅作历史追溯，不与 v2 横向比较。详见 [evals/README.md](./evals/README.md)。

## 快速开始

### 环境要求

- Git、Docker Desktop、Node.js/npm、[uv](https://docs.astral.sh/uv/)
- 官方 `cls-mcp-server`（需要真实 CLS MCP 时）
- Qwen 与 CLS 配置仅在使用相应真实能力时需要

### 1. 获取项目与本地配置

```bash
git clone https://github.com/Shuhong-BNU/OpsPilot.git
cd OpsPilot

cp config/project.template.json config/project.json
cp config/user.project.template.json config/user.project.json
```

`config/project.json` 和 `config/user.project.json` 只保存在本机，已被 Git 忽略。模板不含密钥；禁止提交 API Key、CLS 凭据或用户数据。

### 2. 一键启动

macOS / Linux：

```bash
./scripts/start-local.sh
```

Windows：

```text
scripts\start-local.bat
```

启动器会启动 etcd、MinIO、Milvus、Attu 与 Alertmanager，执行迁移并在本机启动 CLS MCP、后端和前端。

| 服务 | 地址 |
| --- | --- |
| 前端 | `http://127.0.0.1:5173` |
| 后端 | `http://127.0.0.1:8000` |
| 就绪检查 | `http://127.0.0.1:8000/ready` |
| CLS MCP SSE | `http://127.0.0.1:3000/sse` |
| Alertmanager | `http://127.0.0.1:9093` |
| Attu | `http://127.0.0.1:8001` |

更多安装与配置说明： [macOS](docs/setup/macos.md)、[Linux](docs/setup/linux.md)、[Windows](docs/setup/windows.md)、[配置与运维](docs/operations-and-monitoring.md)。

## 项目结构

```text
OpsPilot/
├── apps/
│   ├── backend/                 # FastAPI 服务、Agent、RAG、AIOps、迁移与后端测试
│   │   └── src/opspilot/        # 唯一后端业务 Python 包
│   └── frontend/                # Vue 页面、组件、Pinia stores、API/SSE client 与前端测试
├── packages/api-contracts/      # HTTP、错误码、OpenAPI、SSE 的共享 TypeScript 契约
├── config/                      # 可提交的无密钥模板；本地 JSON 配置由 Git 忽略
├── evals/                       # v2 固定题集、SOP 语料、runner、报告与旧版 baseline
├── infra/                       # etcd、MinIO、Milvus、Attu、Alertmanager 的 Compose 资产
├── scripts/                     # macOS/Linux/Windows 启动器和架构图生成脚本
├── docs/                        # 安装、架构、运维与操作指南
├── openspec/                    # 当前可执行规格、变更记录与历史归档
├── AGENTS.md                    # 仓库实现约束、代码规范与验证要求
├── package.json                 # Node workspace 命令和依赖入口
└── README.md                    # 项目入口与运行说明
```

后端内部按职责划分：

| 路径 | 作用 |
| --- | --- |
| `opspilot/api/` | FastAPI 路由、依赖注入、统一响应与 SSE 入口 |
| `opspilot/auth/` | Argon2 认证、token 哈希与当前用户上下文 |
| `opspilot/chat/` | 会话、流式 Agent、Prompt、Skill、记忆和反馈 |
| `opspilot/retrieval/` | 知识检索工具、BM25L、RRF、rerank、引用与权限过滤 |
| `opspilot/aiops/` | 告警、Plan-Execute-Replan、持久任务、证据和报告 |
| `opspilot/mcp/` | 用户 MCP 连接、工具发现、调用治理与审计 |
| `opspilot/vector_store/` | Milvus 向量存储、chunk 与范围过滤 |
| `opspilot/evaluation/` | Eval v2 的确定性 adapter 和评分逻辑 |
| `apps/backend/alembic/` | SQLite schema migration revisions |

## 常用验证命令

```bash
# 根目录：前端、共享契约、文档与规格
npm run frontend:typecheck
npm run frontend:test
npm run frontend:build
npm run contracts:typecheck
npm --workspace packages/api-contracts run test
npm run docs:build
openspec validate --all

# apps/backend：后端
uv run ruff check .
uv run pyright
uv run pytest
```

## 真实日志与告警操作

上传测试 CLS 日志、发布本地 Alertmanager 告警、索引关联 SOP 与执行完整 AIOps 诊断均为显式操作，不属于日常启动流程。请参阅 [真实日志与告警操作指南](docs/guides/real-log-and-alert.md)。

## 安全边界

- 不提交 `config/project.json`、`config/user.project.json`、API Key、CLS 凭据、用户数据或运行日志。
- 不使用 mock 日志或虚构诊断替代真实 CLS MCP 工具结果。
- 所有用户数据、知识向量、MCP 配置、诊断证据和工具审计均按当前认证用户隔离。
