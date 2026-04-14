# OpsPilot

[English](./README.en.md)

> 基于 RAG 与 MCP 的智能运维助手

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![Milvus](https://img.shields.io/badge/Milvus-Vector%20DB-00B388.svg)](https://milvus.io/)
[![Pytest](https://img.shields.io/badge/Tested%20with-pytest-0A9EDC.svg)](https://pytest.org/)

OpsPilot 面向企业运维场景，提供知识增强问答、意图路由分流、AIOps 智能诊断与工具调用能力，帮助用户完成从问题识别、信息检索到排障建议生成的闭环。

它的重点不是把大模型塞进聊天框，而是把下面这些链路真正串起来：

- 意图识别分流
- RAG + 混合检索 + rerank
- Plan-Execute-Replan 诊断流程
- MCP 工具调用
- 持久化会话与工作流状态
- 轻量监控与关键链路测试

## 项目定位

OpsPilot 更适合被描述为：

> 一个面向企业运维场景的 Agent 工程项目，而不是“包装成生产系统”的 Demo。

它强调的是：

- `intent routing`
- `hybrid retrieval`
- `workflow orchestration`
- `persistent state`
- `observability`

它不刻意强调的是：

- 真实线上生产系统
- 已完整接入真实工单平台
- 已完整落地 Prometheus / MySQL 生产方案
- 多智能体平台
- 未经验证的降本或提效数字

## 核心特性

- 规则优先的意图识别层，将请求分流到 `smalltalk / simple_qa / knowledge_qa / aiops_diagnosis / unsupported`
- 知识问答链路使用 `Milvus dense recall + SQLite FTS5 sparse recall + RRF + rerank`
- AIOps 诊断链路使用 `Plan-Execute-Replan`，支持流式输出诊断过程
- 通过 MCP 客户端接入日志与监控类工具，并记录工具调用日志
- 基于 SQLite 持久化 `sessions / messages / workflow_runs / tool_call_logs / document_chunks`
- 通过 JWT 和 `viewer / operator / admin` 做最小可用权限边界
- 暴露轻量指标与 `/metrics` 接口，支持结构化 JSON 和 Prometheus 文本格式
- 已补关键链路测试，证明系统不是“把多个 Demo 接口拼在一起”

## 技术栈

### 后端

- `FastAPI`
- `Pydantic v2`
- `Uvicorn`
- `SQLite`
- `Loguru`

### Agent / LLM / 检索

- `LangChain`
- `LangGraph`
- `DashScope / Qwen`
- `Milvus`
- `SQLite FTS5`
- `RRF`

### 运维与工具集成

- `MCP (Model Context Protocol)`
- `FastMCP`
- 自定义日志查询与监控查询服务

### 工程化

- `pytest`
- `pytest-cov`
- `ruff`
- `black`
- `mypy`

## 架构分层

建议把 OpsPilot 理解成 5 层：

1. 前端交互层：登录、会话列表、聊天模式切换、AIOps 诊断入口
2. API 接入层：对话、流式对话、上传、会话、鉴权、监控、健康检查
3. 编排服务层：意图识别、链路路由、Plan-Execute-Replan 工作流
4. 检索与工具层：混合检索、知识工具、MCP 工具调用
5. 持久化与观测层：SQLite 状态落库、指标采集、工具调用审计

## 快速开始

### 环境要求

- Python `3.11+`
- Docker Desktop（用于运行 Milvus）
- DashScope API Key（如需启用真实 LLM / Embedding）

### 1. 克隆项目

```bash
git clone https://github.com/Shuhong-BNU/OpsPilot.git
cd OpsPilot
```

### 2. 配置环境变量

复制 [`.env.example`](./.env.example) 为 `.env`，至少确认这些变量：

```env
APP_NAME=OpsPilot
JWT_SECRET=replace-with-a-secure-secret
DASHSCOPE_API_KEY=your-api-key
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### 3. 安装依赖

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

### 4. 启动项目

Windows 推荐：

```powershell
.\start-windows.bat
```

Linux / macOS 推荐：

```bash
docker compose -f vector-database.yml up -d
make start
```

### 5. 访问服务

- Web 界面：`http://localhost:9900`
- API 文档：`http://localhost:9900/docs`
- 健康检查：`http://localhost:9900/health`
- 指标接口：`http://localhost:9900/metrics`

### 默认演示账号

| 角色 | 用户名 | 密码 |
|---|---|---|
| `viewer` | `viewer` | `viewer123` |
| `operator` | `operator` | `operator123` |
| `admin` | `admin` | `admin123` |

## 项目结构

```text
OpsPilot/
├── app/
│   ├── agent/                 # MCP 客户端与 AIOps 编排逻辑
│   ├── api/                   # FastAPI 路由
│   ├── core/                  # Milvus / LLM 基础组件
│   ├── models/                # 请求与响应模型
│   ├── services/              # 鉴权、会话、检索、监控、聊天等服务
│   ├── tools/                 # 知识查询与工具包装
│   └── utils/                 # 日志与通用工具
├── aiops-docs/                # 近真实运维文档样本
├── mcp_servers/               # CLS / Monitor MCP 服务
├── static/                    # 静态前端页面
├── tests/                     # pytest 测试
├── .env.example               # 环境变量模板
├── Makefile                   # Linux / macOS 常用命令
├── start-windows.bat          # Windows 一键启动
├── stop-windows.bat           # Windows 一键停止
├── vector-database.yml        # Milvus Docker Compose
└── OpsPilot_interview_handbook.md
```

## API 接口

### 鉴权

| 功能 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 登录 | `POST` | `/api/auth/login` | 返回 JWT 与角色信息 |
| 当前用户 | `GET` | `/api/auth/me` | 验证登录态 |

### 对话与会话

| 功能 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 普通对话 | `POST` | `/api/chat` | 意图路由后返回完整结果 |
| 流式对话 | `POST` | `/api/chat_stream` | SSE 输出 route / content / done |
| 清空会话 | `POST` | `/api/chat/clear` | 清空单个会话 |
| 会话详情 | `GET` | `/api/chat/session/{session_id}` | 获取会话历史 |
| 会话列表 | `GET` | `/api/sessions` | 获取当前用户全部会话 |
| 删除会话 | `DELETE` | `/api/sessions/{session_id}` | 删除单会话 |

### 运维能力

| 功能 | 方法 | 路径 | 说明 |
|---|---|---|---|
| AIOps 诊断 | `POST` | `/api/aiops` | `operator/admin` 可访问，流式诊断 |
| 文档上传 | `POST` | `/api/upload` | `operator/admin` 可访问，自动索引 |
| 目录索引 | `POST` | `/api/index_directory` | 批量索引目录 |

### 可观测性

| 功能 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 健康检查 | `GET` | `/health` | 检查 API / Milvus / SQLite |
| 指标快照 | `GET` | `/metrics` | JSON 指标 |
| Prometheus 文本 | `GET` | `/metrics?format=prometheus` | Prometheus 格式导出 |

## 配置说明

主要配置集中在 [`.env.example`](./.env.example) 和 [app/config.py](./app/config.py)。

### 应用与服务

| 变量 | 说明 | 默认值 |
|---|---|---|
| `APP_NAME` | 项目名 | `OpsPilot` |
| `APP_TITLE` | 页面标题 | `基于 RAG 与 MCP 的智能运维助手` |
| `HOST` | 服务监听地址 | `0.0.0.0` |
| `PORT` | 服务端口 | `9900` |
| `DEBUG` | 调试模式 | `True/False` |

### 鉴权与持久化

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DATABASE_PATH` | SQLite 文件路径 | `./data/opspilot.db` |
| `JWT_SECRET` | JWT 密钥 | 开发默认值 |
| `JWT_EXPIRE_MINUTES` | 登录态有效期 | `720` |
| `PASSWORD_HASH_ITERATIONS` | PBKDF2 轮数 | `120000` |

### RAG 与检索

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DASHSCOPE_MODEL` | 对话模型 | `qwen-max` |
| `DASHSCOPE_EMBEDDING_MODEL` | 向量模型 | `text-embedding-v4` |
| `RAG_TOP_K` | 回答引用文档数 | `3` |
| `DENSE_TOP_K` | 稠密召回候选数 | `6` |
| `SPARSE_TOP_K` | 稀疏召回候选数 | `6` |
| `HYBRID_TOP_K` | 融合后保留数 | `4` |
| `RERANK_TOP_K` | 重排后保留数 | `3` |

### MCP 与监控

| 变量 | 说明 | 默认值 |
|---|---|---|
| `MCP_CLS_URL` | 日志查询工具地址 | `http://localhost:8003/mcp` |
| `MCP_MONITOR_URL` | 监控工具地址 | `http://localhost:8004/mcp` |
| `METRICS_ENABLED` | 是否开启指标采集 | `True` |

## AIOps 智能运维

OpsPilot 的 AIOps 诊断链路基于 `Plan-Execute-Replan`：

1. Planner 生成诊断计划
2. Executor 调用 MCP 工具执行步骤
3. Replanner 判断是否继续执行或收敛输出
4. 生成最终诊断报告，并将结果持久化到 `workflow_runs`

### 当前可讲的能力点

- 基于告警 / 异常问题触发专门诊断链路
- 通过 MCP 工具查询日志与监控样本
- 流式输出诊断阶段、步骤执行结果与最终报告
- 将工作流耗时、工具调用成功率和会话上下文一并记录

### 推荐表达方式

更适合写成：

> 基于近真实运维文档、告警样本与历史处理经验，构建 AIOps 诊断闭环。

不建议写成：

> 已完整接入真实线上运维平台。

## 测试与可观测性

### 当前测试

已补的测试覆盖：

- 鉴权服务测试
- 意图识别规则测试
- 检索融合与重排测试
- API 权限边界测试

运行方式：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### 当前监控指标

系统会记录：

- 请求量
- 平均响应时延
- RAG 检索耗时
- rerank 耗时
- MCP 工具调用成功率 / 失败率
- AIOps 工作流总耗时

## 开发指南

### 常用命令

```bash
# Linux / macOS
make start
make stop
make restart
make test
make lint
make format
make coverage
```

```powershell
# Windows
.\start-windows.bat
.\stop-windows.bat
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m black app tests
```

### 推荐阅读顺序

1. [app/main.py](./app/main.py)
2. [app/services/chat_service.py](./app/services/chat_service.py)
3. [app/services/intent_service.py](./app/services/intent_service.py)
4. [app/services/retrieval_service.py](./app/services/retrieval_service.py)
5. [app/services/session_service.py](./app/services/session_service.py)
6. [app/services/auth_service.py](./app/services/auth_service.py)
7. [app/agent/mcp_client.py](./app/agent/mcp_client.py)
8. [OpsPilot_interview_handbook.md](./OpsPilot_interview_handbook.md)

## 面试 / 作品集可讲证据

- 有明确的意图识别层，而不是所有请求都走统一 Agent
- 有完整的混合检索链路，而不是单纯“接了个向量库”
- 有状态落库与会话恢复，而不是纯前端 localStorage
- 有角色边界与受限接口，而不是默认全开放
- 有轻量指标与测试，能证明关键路径不是随意拼接

## 常见问题

### 1. Windows 下 `make` 不可用怎么办？

直接使用：

```powershell
.\start-windows.bat
.\stop-windows.bat
```

### 2. 没有配置 DashScope API Key 能运行吗？

可以启动服务与测试，但真实问答、Embedding、检索效果会退化。要完整体验 RAG 与诊断能力，建议配置 `DASHSCOPE_API_KEY`。

### 3. `/health` 返回 Milvus 异常怎么办？

先确认 Docker 已启动，再执行：

```bash
docker compose -f vector-database.yml up -d
```

### 4. 为什么上传接口需要 `operator/admin`？

因为上传与索引属于高风险写操作，项目刻意保留了最小权限边界，便于在面试中讲清安全设计。

### 5. 这个项目是不是生产系统？

不是。更准确的说法是：一个链路完整、结构清晰、表述诚实的 Agent 工程项目原型。

## 当前能力边界

### 已实现

- 意图识别分流
- 混合检索与轻量重排
- Plan-Execute-Replan 诊断流程
- MCP 工具调用
- 会话与工作流状态持久化
- JWT + 角色权限
- 轻量监控与关键测试

### 部分实现

- rerank 目前是轻量实现，不是独立 cross-encoder 服务
- 监控 / 告警 / 工单更适合表述为近真实样本驱动

### 未宣称

- 真实线上生产闭环
- 多智能体平台
- 完整生产级权限系统
- 完整生产级监控平台接入

## 许可证

[MIT License](./LICENSE)
