# OpsPilot

[English](./README.en.md)

> 基于 RAG 与 MCP 的智能运维助手

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![Milvus](https://img.shields.io/badge/Milvus-Vector%20DB-00B388.svg)](https://milvus.io/)
[![Pytest](https://img.shields.io/badge/Tested%20with-pytest-0A9EDC.svg)](https://pytest.org/)

OpsPilot 将对话问答、知识检索、AIOps 诊断和 MCP 工具协同收拢到一套可运行、可演示、可扩展的运维工作台。它既能作为运维 Agent 的项目范例，也适合用于演示检索增强、诊断编排、权限边界和运行状态可视化。

## ✨ 核心亮点

- 🤖 **对话工作台**：普通问答、流式输出、会话历史和执行轨迹统一在同一界面完成
- 🧭 **意图分流**：按 `smalltalk / simple_qa / knowledge_qa / aiops_diagnosis / unsupported` 切换处理链路
- 📚 **混合检索**：组合 `Milvus dense recall + SQLite FTS5 sparse recall + RRF + rerank`
- 🔧 **AIOps 诊断**：基于 `Plan-Execute-Replan` 自动拆解排障步骤并输出诊断结果
- 🔌 **MCP 集成**：同时接入日志查询和监控查询能力，保留工具调用记录
- 💾 **状态持久化**：会话、消息、工作流和工具日志统一落在 SQLite
- 🔐 **权限分层**：`viewer / operator / admin` 角色边界清晰，敏感操作默认受控
- 🪟 **状态面板**：前端可直接查看模型配置、依赖可用性、访问地址和服务健康度
- 🧪 **关键链路测试**：覆盖鉴权、检索、接口权限和系统状态接口

## 🧱 分层设计

- 🖥️ **前端层**：`static/` 提供单页工作台，负责会话、流式渲染、执行轨迹和系统状态展示
- 🌐 **接口层**：`app/api/` 暴露登录、对话、AIOps、文档上传、会话管理、健康检查和状态查询接口
- 🧠 **服务层**：`app/services/` 封装意图识别、RAG 检索、工作流编排、数据库访问和指标采集
- 🤝 **Agent 层**：`app/agent/` 管理 MCP 客户端和 AIOps 规划执行节点
- 🧰 **工具层**：`app/tools/` 为 Agent 暴露知识检索、时间等可调用工具
- 🗃️ **数据层**：SQLite 负责结构化状态，Milvus 负责向量索引，`aiops-docs/` 提供知识样本

## 🛠️ 技术栈

### ⚡ 一眼看懂版

- **框架**：FastAPI + LangChain + LangGraph
- **LLM**：DashScope / Qwen
- **检索**：Milvus + SQLite FTS5 + RRF + rerank
- **状态存储**：SQLite
- **工具协议**：MCP / FastMCP
- **工程化**：pytest + ruff + black + mypy + Loguru

### 🧩 详细技术栈

| 类别 | 技术 | 作用 |
|---|---|---|
| Web 框架 | FastAPI、Uvicorn、sse-starlette | 提供 REST API、SSE 流式对话和 AIOps 流式诊断 |
| LLM / Agent | LangChain、LangGraph、DashScope / Qwen、langchain-qwq | 对话 Agent、AIOps 工作流、工具调用与规划执行 |
| 检索增强 | Milvus、SQLite FTS5、RRF、轻量 rerank | 稠密召回、稀疏召回、候选融合与重排 |
| 工具集成 | MCP、FastMCP、langchain-mcp-adapters | 接入日志查询、监控查询等外部工具 |
| 状态与数据 | SQLite | 会话、消息、工作流、工具日志、文档切片持久化 |
| 工程化 | pytest、pytest-cov、ruff、black、mypy、Loguru | 测试、代码质量、日志与运行时可观测性 |

## 🚀 快速开始

### 🧰 环境要求

- Python `3.11+`
- Docker Desktop
- DashScope API Key（需要真实模型与 Embedding 能力时再配置）

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

如需手动启动：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

docker compose -f vector-database.yml up -d
.\.venv\Scripts\python.exe mcp_servers\cls_server.py
.\.venv\Scripts\python.exe mcp_servers\monitor_server.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 9900
```

## 🔐 演示账号

| 角色 | 用户名 | 密码 |
|---|---|---|
| `viewer` | `viewer` | `viewer123` |
| `operator` | `operator` | `operator123` |
| `admin` | `admin` | `admin123` |

## 🌐 访问入口

- **Web 界面**：`http://localhost:9900`
- **API 文档**：`http://localhost:9900/docs`
- **健康检查**：`http://localhost:9900/health`
- **指标接口**：`http://localhost:9900/metrics`
- **系统状态接口**：`GET /api/system/status`

## 📡 API 速览

| 功能 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 登录 | `POST` | `/api/auth/login` | 返回 JWT 与角色信息 |
| 当前用户 | `GET` | `/api/auth/me` | 校验登录态 |
| 普通对话 | `POST` | `/api/chat` | 意图路由后一次性返回结果 |
| 流式对话 | `POST` | `/api/chat_stream` | SSE 输出 route / content / done |
| 清空会话 | `POST` | `/api/chat/clear` | 清空单个会话 |
| 会话详情 | `GET` | `/api/chat/session/{session_id}` | 获取历史消息 |
| 会话列表 | `GET` | `/api/sessions` | 获取当前用户全部会话 |
| 删除会话 | `DELETE` | `/api/sessions/{session_id}` | 删除单个会话 |
| AIOps 诊断 | `POST` | `/api/aiops` | `operator/admin` 可访问，流式诊断 |
| 文件上传 | `POST` | `/api/upload` | `operator/admin` 可访问，自动索引文档 |
| 批量索引 | `POST` | `/api/index_directory` | 批量索引目录 |
| 系统状态 | `GET` | `/api/system/status` | 返回模型、依赖和访问地址状态 |
| 健康检查 | `GET` | `/health` | 检查 API / Milvus / SQLite |
| 指标快照 | `GET` | `/metrics` | 返回 JSON 指标 |

## 🗂️ 项目结构

### 🧭 目录职责速览

- `app/`：应用核心，包含接口、服务、Agent、模型和工具实现
- `aiops-docs/`：运维知识样本，适合做检索和诊断演示
- `mcp_servers/`：日志查询与监控查询两个 MCP 服务
- `static/`：单页前端工作台
- `tests/`：核心接口与服务测试
- `docs/assets/`：截图素材和素材维护说明
- `data/`、`logs/`、`uploads/`、`volumes/`：运行时生成的数据、日志、上传缓存和容器卷目录

### 🧩 逐目录逐文件索引

```text
OpsPilot/
├── app/                                      # 应用核心
│   ├── __init__.py                           # 包初始化
│   ├── main.py                               # FastAPI 入口、路由注册、静态资源挂载
│   ├── config.py                             # 应用、模型、检索、MCP、监控配置
│   ├── api/                                  # HTTP 接口层
│   │   ├── __init__.py                       # API 包初始化
│   │   ├── auth.py                           # 登录与当前用户接口
│   │   ├── chat.py                           # 普通对话与流式对话接口
│   │   ├── aiops.py                          # AIOps 流式诊断接口
│   │   ├── file.py                           # 文档上传与目录索引接口
│   │   ├── health.py                         # 健康检查接口
│   │   ├── metrics.py                        # JSON / Prometheus 指标接口
│   │   ├── sessions.py                       # 会话列表、详情、删除接口
│   │   ├── system.py                         # 系统状态与依赖就绪信息接口
│   │   └── dependencies.py                   # 鉴权与角色依赖
│   ├── services/                             # 业务服务层
│   │   ├── __init__.py                       # 服务包初始化
│   │   ├── auth_service.py                   # 默认账号、密码校验、JWT 生成
│   │   ├── chat_service.py                   # 对话主入口与链路调度
│   │   ├── intent_service.py                 # 意图识别与规则分流
│   │   ├── rag_agent_service.py              # RAG Agent 与工具调用编排
│   │   ├── aiops_service.py                  # AIOps 工作流编排
│   │   ├── retrieval_service.py              # 混合检索、RRF、rerank、trace 记录
│   │   ├── session_service.py                # 会话、消息、工作流持久化
│   │   ├── database_service.py               # SQLite 建表、查询、FTS5 检索
│   │   ├── metrics_service.py                # 运行指标采集与输出
│   │   ├── runtime_status_service.py         # 聚合系统状态、模型配置和依赖可用性
│   │   ├── request_context_service.py        # 请求上下文工具
│   │   ├── vector_store_manager.py           # Milvus VectorStore 封装
│   │   ├── vector_embedding_service.py       # DashScope Embedding 封装
│   │   ├── vector_index_service.py           # 文档读取、切片、索引构建
│   │   ├── vector_search_service.py          # 向量检索能力
│   │   └── document_splitter_service.py      # Markdown / 文本文档切片
│   ├── agent/                                # Agent 协同层
│   │   ├── __init__.py                       # Agent 包初始化
│   │   ├── mcp_client.py                     # MultiServer MCP 客户端
│   │   └── aiops/                            # AIOps 工作流节点
│   │       ├── __init__.py                   # AIOps 节点包初始化
│   │       ├── planner.py                    # 规划节点
│   │       ├── executor.py                   # 工具执行节点
│   │       ├── replanner.py                  # 重规划节点
│   │       ├── state.py                      # 工作流状态定义
│   │       └── utils.py                      # 节点辅助函数
│   ├── models/                               # Pydantic 数据模型
│   │   ├── __init__.py                       # 模型包初始化
│   │   ├── auth.py                           # 登录请求与响应模型
│   │   ├── request.py                        # 对话与清空请求模型
│   │   ├── response.py                       # 通用响应模型
│   │   ├── aiops.py                          # AIOps 请求与响应模型
│   │   ├── session.py                        # 会话响应模型
│   │   └── document.py                       # 文档索引相关模型
│   ├── tools/                                # Agent 可调用工具
│   │   ├── __init__.py                       # 工具包初始化
│   │   ├── knowledge_tool.py                 # 知识检索工具
│   │   └── time_tool.py                      # 时间工具
│   ├── core/                                 # 底层能力封装
│   │   ├── __init__.py                       # Core 包初始化
│   │   ├── llm_factory.py                    # LLM 创建工厂
│   │   └── milvus_client.py                  # Milvus 连接与 collection 管理
│   └── utils/                                # 通用工具
│       ├── __init__.py                       # Utils 包初始化
│       └── logger.py                         # Loguru 日志初始化
├── aiops-docs/                               # 运维知识样本
│   ├── cpu_high_usage.md                     # CPU 高负载排障样本
│   ├── disk_high_usage.md                    # 磁盘过高排障样本
│   ├── memory_high_usage.md                  # 内存异常排障样本
│   ├── service_unavailable.md                # 服务不可用排障样本
│   └── slow_response.md                      # 慢响应排障样本
├── mcp_servers/                              # MCP 服务
│   ├── cls_server.py                         # 日志查询 MCP 服务
│   ├── monitor_server.py                     # 监控查询 MCP 服务
│   └── README.md                             # MCP 服务说明
├── static/                                   # 前端工作台
│   ├── index.html                            # 页面结构
│   ├── app.js                                # 前端交互逻辑、状态面板、执行轨迹
│   └── styles.css                            # 视觉样式
├── tests/                                    # 自动化测试
│   ├── conftest.py                           # 测试夹具与公共初始化
│   ├── test_api_security.py                  # API 权限边界测试
│   ├── test_auth_service.py                  # 鉴权服务测试
│   ├── test_intent_service.py                # 意图识别测试
│   ├── test_retrieval_service.py             # 检索与重排测试
│   └── test_system_status_api.py             # 系统状态接口测试
├── docs/                                     # 补充文档与素材
│   └── assets/                               # 截图素材与素材规范
│       ├── README.md                         # 截图命名、分辨率和补图清单
│       └── screenshots/                      # README 截图资源目录
├── data/                                     # 运行生成的 SQLite 数据目录
├── logs/                                     # 运行日志目录
├── uploads/                                  # 上传文件缓存目录
├── volumes/                                  # Milvus 相关持久卷目录
├── .env.example                              # 环境变量模板
├── Makefile                                  # Linux / macOS 常用命令
├── OpsPilot_demo_script.md                   # 演示讲解脚本
├── OpsPilot_interview_handbook.md            # 面试与项目讲解手册
├── pyproject.toml                            # 依赖、格式化、测试配置
├── pyrightconfig.json                        # Pyright 配置
├── start-windows.bat                         # Windows 一键启动脚本
├── stop-windows.bat                          # Windows 一键停止脚本
├── vector-database.yml                       # Milvus Docker Compose 配置
├── README.md                                 # 中文说明
└── README.en.md                              # 英文说明
```

## 📚 文档索引

- [OpsPilot_demo_script.md](./OpsPilot_demo_script.md)：演示顺序、提示词和讲解节奏
- [OpsPilot_interview_handbook.md](./OpsPilot_interview_handbook.md)：项目讲解与问答准备
- [mcp_servers/README.md](./mcp_servers/README.md)：MCP 服务补充说明
- [docs/assets/README.md](./docs/assets/README.md)：截图素材维护规范

## ⚙️ 关键配置

### 🧪 应用与模型

| 变量 | 说明 | 默认值 |
|---|---|---|
| `APP_NAME` | 应用名称 | `OpsPilot` |
| `APP_TITLE` | 页面标题 | `基于 RAG 与 MCP 的智能运维助手` |
| `DASHSCOPE_API_KEY` | DashScope API Key | 空 |
| `DASHSCOPE_MODEL` | 主对话模型 | `qwen-max` |
| `DASHSCOPE_EMBEDDING_MODEL` | 向量模型 | `text-embedding-v4` |
| `DASHSCOPE_RERANK_MODEL` | 重排模型 | `qwen3-rerank` |

### 🗃️ 存储与检索

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DATABASE_PATH` | SQLite 数据库路径 | `./data/opspilot.db` |
| `MILVUS_HOST` | Milvus 地址 | `localhost` |
| `MILVUS_PORT` | Milvus 端口 | `19530` |
| `RAG_TOP_K` | 最终引用文档数 | `3` |
| `DENSE_TOP_K` | 稠密召回候选数 | `6` |
| `SPARSE_TOP_K` | 稀疏召回候选数 | `6` |
| `HYBRID_TOP_K` | 融合后保留数 | `4` |
| `RERANK_TOP_K` | 重排后保留数 | `3` |

### 🔐 鉴权与运行状态

| 变量 | 说明 | 默认值 |
|---|---|---|
| `JWT_SECRET` | JWT 密钥 | 开发默认值 |
| `JWT_EXPIRE_MINUTES` | JWT 有效期 | `720` |
| `PASSWORD_HASH_ITERATIONS` | PBKDF2 轮数 | `120000` |
| `MCP_CLS_URL` | CLS MCP 地址 | `http://localhost:8003/mcp` |
| `MCP_MONITOR_URL` | Monitor MCP 地址 | `http://localhost:8004/mcp` |
| `METRICS_ENABLED` | 是否启用指标采集 | `True` |

## 🎯 AIOps 诊断链路

1. **Planner** 生成诊断计划
2. **Executor** 调用 MCP 工具执行步骤
3. **Replanner** 判断继续执行、调整计划或结束
4. **Reporter** 汇总诊断结果并写入 `workflow_runs`

适合演示的典型场景：

- CPU / 内存 / 磁盘等资源告警
- 服务不可用与慢响应排查
- 结合日志、监控和知识库的诊断问答

## 🎬 演示与录屏

- `viewer` 账号适合演示普通问答、知识问答和流式回复
- `operator` 账号适合演示 AIOps 诊断、文档上传和系统状态查看
- 前端右侧工作区适合截取回答内容，左侧面板适合截取会话历史、执行轨迹和系统状态
- 录屏脚本和截图规范分别放在 [OpsPilot_demo_script.md](./OpsPilot_demo_script.md) 与 [docs/assets/README.md](./docs/assets/README.md)

## 🧪 测试与观测

### ✅ 当前测试覆盖

- 鉴权服务测试
- 意图识别规则测试
- 混合检索与重排测试
- API 权限边界测试
- 系统状态接口测试

### ▶️ 运行测试

```bash
make test
make coverage
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

### 📈 当前指标

- HTTP 请求总量
- 请求平均时延
- 稠密检索耗时
- 稀疏检索耗时
- rerank 耗时
- MCP 工具调用成功率 / 失败率
- AIOps 工作流总耗时

## 🧭 开发命令

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

## ❓ 常见问题

### 🪟 Windows 下 `make` 不可用怎么办？

优先使用：

```powershell
.\start-windows.bat
.\stop-windows.bat
```

### 🔑 没有配置 DashScope API Key 能运行吗？

可以启动服务、跑测试和浏览页面，但真实问答、Embedding 和混合检索效果会退化。完整演示建议配置 `DASHSCOPE_API_KEY`。

### 🐳 `/health` 返回 Milvus 异常怎么办？

先确认 Docker Desktop 已启动，再执行：

```bash
docker compose -f vector-database.yml up -d
```

### 📤 上传文档为什么会失败？

常见原因：

- 当前账号不是 `operator/admin`
- 请求头里没有携带 `Authorization: Bearer <token>`

### 🧪 这是生产系统吗？

当前更适合作为链路完整、结构清晰、边界明确的智能运维 Agent 工程样例和演示项目。
