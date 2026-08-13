# OpsPilot GitHub 文件索引

本文档说明 `main` 分支中每一类已提交文件的用途，并把重复结构的 OpenSpec 历史文件逐条归入对应变更。编写时 `main` 有 815 个 Git 跟踪文件；本地 `config/project.json`、`config/user.project.json`、运行数据库、日志、缓存、依赖目录和个人笔记均被忽略，不属于 GitHub 内容。

## 根目录

| 文件 | 用途 |
| --- | --- |
| `.dockerignore` | 控制 Docker 构建上下文，排除本地依赖、缓存和运行数据。 |
| `.gitignore` | 排除密钥配置、运行产物、私有路线图、私有变更理由与个人提示词。 |
| `AGENTS.md` | 给维护者的实现边界、代码规范、配置安全和验证要求。 |
| `README.md` | GitHub 项目入口：功能、架构、启动、Eval、验证与安全边界。 |
| `package.json` | Node workspace 根命令和开发依赖。 |
| `package-lock.json` | npm 依赖版本锁定，保证前端安装可复现。 |

## 后端：运行、配置与迁移

| 文件 | 用途 |
| --- | --- |
| `apps/backend/README.md` | 后端应用的安装、配置和验证说明。 |
| `apps/backend/pyproject.toml` | Python 包元数据、运行/开发依赖、Ruff 与 Pyright 配置。 |
| `apps/backend/uv.lock` | Python 依赖锁文件。 |
| `apps/backend/alembic.ini` | Alembic 迁移工具配置。 |
| `apps/backend/alembic/env.py` | Alembic 运行环境，连接配置与 metadata 装配。 |
| `apps/backend/alembic/versions/202607080001_create_memory_schema.py` | 建立 SQLite 基础业务数据表。 |
| `apps/backend/alembic/versions/202607080002_add_auth_schema.py` | 增加用户、密码哈希和 token 相关表。 |
| `apps/backend/alembic/versions/202607080003_add_tenant_scope.py` | 增加 tenant/user 隔离字段和索引。 |
| `apps/backend/alembic/versions/202607090001_add_knowledge_documents.py` | 增加知识库、文档与 chunk 元数据表。 |
| `apps/backend/alembic/versions/202607090002_add_document_index_tasks.py` | 增加文档索引任务持久化表。 |
| `apps/backend/alembic/versions/202607100001_add_agent_tool_call_audits.py` | 增加 Agent/MCP 工具调用审计表。 |
| `apps/backend/alembic/versions/202607100002_add_aiops_evidence_chain.py` | 增加诊断计划、步骤、证据和报告表。 |
| `apps/backend/alembic/versions/202607100003_add_structured_diagnosis_cases.py` | 增加结构化诊断案例表。 |
| `apps/backend/alembic/versions/202607110001_add_user_chat_configurations.py` | 增加用户 Prompt 与聊天配置表。 |
| `apps/backend/alembic/versions/202607110002_add_user_chat_assets.py` | 增加聊天附件与用户资产表。 |
| `apps/backend/alembic/versions/202607110003_add_chat_memory_state.py` | 增加会话记忆压缩状态表。 |
| `apps/backend/alembic/versions/202607110004_add_chat_skill_metadata.py` | 增加渐进式 Skill 元数据表。 |
| `apps/backend/alembic/versions/202607110005_add_background_job_runtime.py` | 增加 durable job、事件、租约和重试状态表。 |
| `apps/backend/alembic/versions/202607110006_add_user_feedback.py` | 增加回答、引用和诊断反馈表。 |
| `apps/backend/alembic/versions/202607110007_add_mcp_connections.py` | 增加用户 MCP 连接配置表。 |

所有上述 revision 文件都在 `apps/backend/alembic/versions/` 下，按文件名时间顺序执行；不得修改已发布 revision，应新增 revision。

## 后端：业务源码

以下 12 个包初始化文件均用于定义 Python 包的公开导出或包标识：`src/opspilot/__init__.py`、`src/opspilot/aiops/__init__.py`、`src/opspilot/api/__init__.py`、`src/opspilot/auth/__init__.py`、`src/opspilot/chat/__init__.py`、`src/opspilot/documents/__init__.py`、`src/opspilot/evaluation/__init__.py`、`src/opspilot/jobs/__init__.py`、`src/opspilot/llm/__init__.py`、`src/opspilot/memory/__init__.py`、`src/opspilot/retrieval/__init__.py`、`src/opspilot/vector_store/__init__.py`；这些路径均相对于 `apps/backend/`。

| 文件 | 用途 |
| --- | --- |
| `src/opspilot/foundation.py` | 基础领域类型、协议和通用值对象。 |
| `src/opspilot/project_config.py` | 读取、合并并校验本地 JSON 项目配置。 |
| `src/opspilot/error_catalog.py` | 统一 API 错误码、错误消息和转换规则。 |
| `src/opspilot/observability.py` | 请求日志、敏感字段脱敏和基础指标。 |
| `src/opspilot/alerts.py` | Prometheus/Alertmanager 活跃告警适配与筛选。 |
| `src/opspilot/feedback.py` | 用户对回答、引用和诊断的反馈服务。 |
| `src/opspilot/mcp_client.py` | MCP SSE 客户端、真实工具调用与错误处理。 |
| `src/opspilot/mcp_connections.py` | 用户级 MCP 连接的存储、检查、启停与工具发现。 |
| `src/opspilot/api/app.py` | FastAPI 应用工厂、生命周期、路由与依赖装配。 |
| `src/opspilot/api/observability.py` | 健康、就绪、配置检查和指标 HTTP 端点。 |
| `src/opspilot/api/responses.py` | 统一成功/失败 response envelope。 |
| `src/opspilot/auth/repositories.py` | 认证数据访问 Protocol 与仓库接口。 |
| `src/opspilot/auth/sqlite.py` | SQLite 认证仓库实现。 |
| `src/opspilot/auth/service.py` | 注册、登录、注销、Argon2 密码与 token 哈希业务逻辑。 |
| `src/opspilot/chat/configuration.py` | Prompt、Skill 与聊天配置管理。 |
| `src/opspilot/chat/memory.py` | 会话历史压缩、记忆模式和上下文占用处理。 |
| `src/opspilot/chat/streaming.py` | LangChain Agent、SSE 事件和聊天会话编排。 |
| `src/opspilot/documents/policy.py` | 文档上传类型、大小、切分与权限规则。 |
| `src/opspilot/documents/extraction.py` | Markdown/PDF 内容提取和 chunk 预览。 |
| `src/opspilot/documents/indexing.py` | 后台索引、重试、向量写入和文档状态流转。 |
| `src/opspilot/retrieval/hybrid.py` | 分词、BM25L、RRF 与混合候选计算。 |
| `src/opspilot/retrieval/tool.py` | 生产 `KnowledgeRetrievalTool`、范围过滤、引用和阶段排名证据。 |
| `src/opspilot/vector_store/config.py` | Milvus collection 和向量存储配置。 |
| `src/opspilot/vector_store/schema.py` | 向量 chunk、检索结果与范围字段数据结构。 |
| `src/opspilot/vector_store/milvus.py` | Milvus 建库、写入、搜索、删除与权限过滤实现。 |
| `src/opspilot/llm/config.py` | Qwen/OpenAI-compatible 模型配置解析。 |
| `src/opspilot/llm/provider.py` | Chat/embedding 模型提供者工厂。 |
| `src/opspilot/llm/rerank.py` | Qwen rerank 调用、响应解析和失败语义。 |
| `src/opspilot/memory/models.py` | SQLAlchemy 业务实体模型。 |
| `src/opspilot/memory/database.py` | SQLite engine、session 和数据库初始化。 |
| `src/opspilot/memory/sqlite.py` | 基础 SQLite repository 实现。 |
| `src/opspilot/memory/extended_sqlite.py` | 扩展业务查询和事务辅助。 |
| `src/opspilot/memory/repositories.py` | 聊天、知识、任务、证据等仓库接口与实现。 |
| `src/opspilot/memory/vector_scope.py` | 向量 owner、tenant、知识库范围条件生成。 |
| `src/opspilot/jobs/runtime.py` | 可恢复后台任务的领取、租约、心跳、取消、超时与重试。 |
| `src/opspilot/aiops/diagnostics.py` | LangGraph Plan-Execute-Replan-Report 诊断图与 SSE 事件。 |
| `src/opspilot/aiops/cases.py` | 诊断历史、报告、证据和案例库沉淀。 |
| `src/opspilot/aiops/fixtures.py` | Java 电商故障样例的结构化定义。 |
| `src/opspilot/evaluation/offline_retrieval.py` | Eval v2 确定性外部 adapter、单题评分和阶段证据。 |

## 后端：显式操作脚本

| 文件 | 用途 |
| --- | --- |
| `scripts/generate_and_upload_cls_logs.py` | 生成并上传 CLS 结构化测试日志。 |
| `scripts/publish_ecommerce_quant_alert.py` | 发布量化定价延迟样例告警。 |
| `scripts/publish_java_ecommerce_alerts.py` | 发布 Java 电商场景的本地 Alertmanager 告警。 |
| `scripts/seed_ecommerce_aiops_sop.py` | 上传单个量化定价 SOP。 |
| `scripts/seed_java_ecommerce_aiops_sops.py` | 上传并等待索引 Java 电商 SOP 集。 |

## 后端：测试文件

每个 `apps/backend/tests/test_*.py` 是对应行为的 pytest 覆盖：

| 文件 | 覆盖目标 |
| --- | --- |
| `test_active_alerts.py` | 活跃告警查询与用户范围。 |
| `test_aiops_diagnostics.py` | AIOps 图、事件、任务状态与报告。 |
| `test_asyncio_configuration.py` | asyncio 和应用运行时初始化约束。 |
| `test_auth_api.py` | 注册、登录、登出和认证 API。 |
| `test_auth_migrations.py` | 认证相关迁移可升级性。 |
| `test_auth_service.py` | 密码哈希、token 与认证服务。 |
| `test_chat_memory.py` | 会话记忆模式和压缩。 |
| `test_chat_sessions_api.py` | 会话 CRUD 与用户隔离。 |
| `test_document_indexing.py` | 文档切分、索引任务和重试。 |
| `test_document_indexing_api.py` | 文档上传、索引 API 与状态。 |
| `test_ecommerce_aiops_fixtures.py` | 电商故障样例的一致性。 |
| `test_environment_examples.py` | 配置模板与环境样例边界。 |
| `test_extended_capabilities.py` | 扩展平台能力集成。 |
| `test_foundation.py` | 基础类型、协议和项目约束。 |
| `test_hybrid_retrieval.py` | BM25L、RRF 和混合检索算法。 |
| `test_infra_compose.py` | Compose 基础设施定义。 |
| `test_knowledge_documents_api.py` | 知识库和文档管理 API。 |
| `test_knowledge_retrieval_api.py` | 检索 API response 与权限。 |
| `test_knowledge_retrieval_tool.py` | `KnowledgeRetrievalTool` 行为和引用证据。 |
| `test_llm_provider.py` | Qwen provider、embedding 与 rerank 配置。 |
| `test_local_development_docs.py` | README、安装和操作文档链接/命令。 |
| `test_mcp_observability.py` | MCP 调用审计与可观测性。 |
| `test_memory_migrations.py` | 业务库迁移链。 |
| `test_memory_repositories.py` | Repository 持久化与权限过滤。 |
| `test_milvus_vector_store.py` | Milvus schema、写入、搜索和删除。 |
| `test_observability.py` | 结构化日志、脱敏和指标。 |
| `test_offline_retrieval_evaluation.py` | Eval v2 adapter 与评分证据。 |
| `test_readiness_api.py` | health、ready 与 config check。 |
| `test_rerank_model.py` | rerank 请求、排序和失败处理。 |
| `test_skill_examples.py` | 内置 SKILL.md 示例的格式。 |
| `test_stream_rag_chat_api.py` | 聊天 SSE 顺序、终止和错误语义。 |
| `test_tool_call_audits.py` | 工具调用审计生命周期。 |
| `test_vector_scope.py` | 向量 owner/tenant/知识库范围过滤。 |

## 前端：构建与源码

| 文件 | 用途 |
| --- | --- |
| `apps/frontend/package.json` | 前端依赖和 Vite/Vitest 命令。 |
| `apps/frontend/tsconfig.json` | strict TypeScript 编译选项。 |
| `apps/frontend/vite.config.ts` | Vite、Vue 与 Vitest 配置。 |
| `apps/frontend/env.d.ts` | Vite/TypeScript 环境类型。 |
| `apps/frontend/index.html` | Vite 应用 HTML 入口。 |
| `src/main.ts` | Vue 应用挂载、Pinia 和 router 注册。 |
| `src/App.vue` | 顶层应用壳。 |
| `src/styles.css` | 全局样式、响应式与无障碍视觉规则。 |
| `src/foundation.ts` | 前端共享领域类型与常量。 |
| `src/config.ts` | 前端运行地址与配置。 |
| `src/runtimeHealth.ts` | 后端可用性状态检查。 |
| `src/authClient.ts` / `src/authState.ts` | 认证 API 调用与登录状态恢复。 |
| `src/protectedDataClient.ts` / `src/protectedDataState.ts` | 受保护数据请求和状态。 |
| `src/api/apiClient.ts` | 统一 typed HTTP client 与错误转换。 |
| `src/api/sseClient.ts` | SSE 解析、取消和终止语义。 |
| `src/chat/chatClient.ts` | 聊天会话、流式消息和配置请求。 |
| `src/chat/retrievalPresentation.ts` | 检索引用和阶段证据展示转换。 |
| `src/aiops/aiopsClient.ts` | 告警、诊断、报告与案例 API/SSE 请求。 |
| `src/knowledge/knowledgeClient.ts` | 知识库、文档与索引请求。 |
| `src/knowledge/documentPolicy.ts` | 前端上传限制和切分参数校验。 |
| `src/mcp/mcpClient.ts` | MCP 连接管理与工具发现请求。 |
| `src/feedback/userFeedbackClient.ts` | 回答、引用和诊断反馈请求。 |
| `src/router/index.ts` | 登录保护、路由与页面映射。 |
| `src/layouts/WorkspaceLayout.vue` | 受保护工作台通用布局。 |
| `src/views/AuthView.vue` | 登录与注册页面。 |
| `src/views/ChatView.vue` | 聊天工作台页面。 |
| `src/views/KnowledgeView.vue` | 知识库页面。 |
| `src/views/AiopsView.vue` | 告警和诊断页面。 |
| `src/views/McpView.vue` | MCP 连接管理页面。 |
| `src/views/WorkspacePlaceholderView.vue` | 暂未开放路由的占位页面。 |

### 前端组件和 store

| 文件 | 用途 |
| --- | --- |
| `components/WorkspaceNavigation.vue` | 工作台导航。 |
| `components/AppFeedback.vue` | 全局成功、提示和错误反馈。 |
| `components/AppLoadingState.vue` / `AppEmptyState.vue` / `AppErrorState.vue` | 通用加载、空态和错误态。 |
| `components/AsyncStatusBadge.vue` | 后台任务状态徽标。 |
| `components/ChatComposer.vue` | 聊天输入和提交。 |
| `components/ChatTranscript.vue` | 消息流、工具过程和流式渲染。 |
| `components/ChatSessionList.vue` | 会话创建、切换、删除列表。 |
| `components/ChatPromptSidebar.vue` | Prompt 管理侧栏。 |
| `components/ChatSkillSidebar.vue` | Skill 上传和选择侧栏。 |
| `components/ChatCitationDetail.vue` | 单条知识引用详情。 |
| `components/RetrievalStageTrace.vue` | vector、BM25、RRF、rerank 排名证据。 |
| `components/UserFeedbackControl.vue` | 内容反馈控件。 |
| `components/MarkdownContent.vue` | 安全 Markdown 渲染。 |
| `components/KnowledgeUpload.vue` | 上传、切分设置与预览。 |
| `components/KnowledgeDocumentList.vue` | 文档和索引任务列表。 |
| `components/KnowledgeDocumentDetail.vue` | 文档详情与操作。 |
| `components/ActiveAlertList.vue` | 活动告警列表。 |
| `components/AiopsRunForm.vue` | 启动/取消诊断表单。 |
| `components/AiopsTimeline.vue` | 诊断 SSE 步骤时间线。 |
| `components/AiopsEvidenceChain.vue` | 诊断证据链。 |
| `components/AiopsReportPanel.vue` | Markdown 诊断报告。 |
| `components/AiopsHistory.vue` | 历史诊断任务。 |
| `components/AiopsCaseLibrary.vue` | 案例库浏览与沉淀。 |
| `stores/auth.ts` | 登录用户与 token 状态。 |
| `stores/chat.ts` | 会话、消息、流式状态和 Prompt/Skill 状态。 |
| `stores/knowledge.ts` | 知识库、文档和索引任务状态。 |
| `stores/aiops.ts` | 告警、诊断、证据和报告状态。 |
| `stores/mcp.ts` | MCP 连接与发现的工具状态。 |
| `stores/feedback.ts` / `stores/userFeedback.ts` | 全局反馈和内容反馈状态。 |
| `ui/asyncStatus.ts` | 异步状态到中文 UI 文案的映射。 |
| `ui/userFacingError.ts` | 后端错误到用户提示的映射。 |

### 前端测试

每个 `apps/frontend/tests/*.test.ts` 直接覆盖同名领域：`activeAlerts` 告警；`aiopsComponents`、`aiopsLayout`、`aiopsStore` 诊断 UI；`appShellComponents`、`appShellRouter`、`appShellTransport` 应用壳；`auth` 认证；`chatAssemblySettings`、`chatComponents`、`chatLayout`、`chatStore` 聊天；`chineseWorkspace` 中文文案；`contracts` 共享契约；`foundation` 基础类型；`knowledgeComponents`、`knowledgeLayout`、`knowledgeStore` 知识库；`markdownContent` Markdown；`protectedData` 权限数据；`runtimeHealth` 健康检查；`workspaceLayout` 工作台布局。

## 共享契约、配置、基础设施与评测

| 文件 | 用途 |
| --- | --- |
| `packages/api-contracts/package.json` / `tsconfig.json` | 契约包依赖和 strict 编译配置。 |
| `src/index.ts` | 契约公共导出。 |
| `src/auth.ts` | 认证请求和响应类型。 |
| `src/chat.ts` | 聊天、会话和引用类型。 |
| `src/chat-configuration.ts` | Prompt、Skill、记忆配置类型。 |
| `src/documents.ts` | 知识库、文档、chunk 和上传类型。 |
| `src/indexing.ts` | 索引任务类型。 |
| `src/retrieval.ts` | 检索结果与阶段排名类型。 |
| `src/vector.ts` | 向量存储请求/结果类型。 |
| `src/mcp.ts` | MCP 连接、工具发现和审计类型。 |
| `src/background-jobs.ts` | durable job 和事件类型。 |
| `src/feedback.ts` | 用户反馈类型。 |
| `src/protected-data.ts` | 用户范围数据类型。 |
| `src/responses.ts` / `src/errors.ts` | 通用 envelope 和错误码类型。 |
| `src/sse.ts` | 聊天和诊断 SSE 事件联合类型。 |
| `src/openapi.ts` | OpenAPI 描述和 API 元数据。 |
| `tests/api-contracts.test.ts` | 所有公共类型、错误码和 SSE 合同测试。 |
| `config/project.template.json` | 不含密钥的基础本地配置模板。 |
| `config/user.project.template.json` | 不含密钥的个人覆盖配置模板。 |
| `infra/compose.yaml` | etcd、MinIO、Milvus、Attu、Alertmanager 本地 Compose 栈。 |
| `infra/alertmanager/alertmanager.yml` | Alertmanager 路由与接收器配置。 |
| `infra/README.md` | 基础设施启动、地址和安全边界说明。 |
| `scripts/start-local.sh` | macOS/Linux 完整本机启动器。 |
| `scripts/start-local.bat` | Windows 完整本机启动器。 |
| `scripts/generate_architecture_diagrams.py` | 生成项目文档使用的架构图。 |
| `evals/run_retrieval_eval.py` | Eval v2 runner，读取固定题集、写 JSONL 结果和 Markdown 报告。 |
| `evals/datasets/opspilot_rag_cases.jsonl` | 10 条带相关 SOP 标注的固定检索题。 |
| `evals/corpus/cpu_high_usage.md` | CPU 高使用率 SOP 语料。 |
| `evals/corpus/memory_high_usage.md` | 内存高/OOM SOP 语料。 |
| `evals/corpus/disk_high_usage.md` | 磁盘高使用率 SOP 语料。 |
| `evals/corpus/service_unavailable.md` | 服务不可用 SOP 语料。 |
| `evals/corpus/slow_response.md` | 慢响应 SOP 语料。 |
| `evals/README.md` / `README.en.md` | Eval v2 的中英文边界、执行和指标说明。 |
| `evals/baselines/v1/*` | 迁移前 v1 的 metadata、原始结果和报告，只作历史追溯。 |
| `evals/baselines/v1.1/*` | 迁移前 v1.1 的 metadata、原始结果和报告，只作历史追溯。 |

## 文档与 Skill 示例

| 文件 | 用途 |
| --- | --- |
| `docs/.vitepress/config.mts` | VitePress 标题、导航、侧栏和本地搜索配置。 |
| `docs/index.md` | 文档站首页。 |
| `docs/foundation.md` | 项目基础架构说明。 |
| `docs/operations-and-monitoring.md` | 本地配置、凭据安全和运维说明。 |
| `docs/guides/real-log-and-alert.md` | 真实 CLS 日志、告警、SOP 与诊断操作。 |
| `docs/aiops/ecommerce-aiops-fixture.md` | Java 电商故障样例总说明。 |
| `docs/aiops/ecommerce-quant-pricing-latency-sop.md` | 量化定价延迟 SOP 样例。 |
| `docs/setup/macos.md` / `linux.md` / `windows.md` | 三个平台安装与启动步骤。 |
| `docs/examples/skills/README.md` | 项目内 Skill 示例说明。 |
| `api-troubleshooting/SKILL.md` | API 故障排查 Skill。 |
| `change-risk-review/SKILL.md` | 变更风险审查 Skill。 |
| `incident-report/SKILL.md` | 故障报告 Skill。 |
| `knowledge-search/SKILL.md` | 知识检索 Skill。 |
| `log-analysis/SKILL.md` | 日志分析 Skill。 |
| `docs/changes/index.md` | 变更 WIKI 索引。 |
| `docs/changes/migrate-opspilot-platform-and-add-offline-eval/index.md` | 当前迁移与 Eval v2 变更的 WIKI 页面。 |
| `docs/changes/archive/<change>/index.md`（65 个） | 每一条已归档 OpenSpec 变更的 WIKI 页面，引用其源 proposal、design、tasks 和 delta specs。 |
| `docs/openspec` | 文档站链接到 OpenSpec 源目录的入口。 |

## OpenSpec：当前规格和变更源文件

`openspec/config.yaml` 是 OpenSpec 仓库配置。`openspec/specs/<capability>/spec.md` 是当前生效的能力规格；以下每个文件各自定义同名能力的 Requirement 和 Scenario：

`active-alert-subscription-entry`、`agent-tool-call-audits`、`aiops-diagnosis-tasks`、`aiops-diagnosis-ui`、`aiops-evidence-chain`、`api-and-sse-contracts`、`authorization-and-tenant-isolation`、`automated-diagnosis-case-library`、`background-job-runtime`、`chat-experience`、`chat-memory-management`、`chat-prompt-skill-configuration`、`chat-sessions`、`chinese-ai-workspace-experience`、`cls-log-generation`、`diagnosis-case-knowledge`、`docker-compose-startup`、`document-chunking-strategies`、`document-indexing-jobs`、`ecommerce-aiops-fixtures`、`frontend-end-to-end-validation`、`knowledge-answer-citation-view`、`knowledge-base-ui`、`knowledge-documents`、`knowledge-retrieval-tool`、`local-development-operations-guide`、`mcp-connection-management`、`memory-repositories`、`milvus-vector-store`、`openspec-wiki`、`platform-installation-guides`、`project-foundation`、`qwen-openai-provider`、`real-mcp-tools`、`repo-hygiene`、`request-observability`、`runtime-readiness-checks`、`shared-user-project-configuration`、`stream-rag-chat`、`user-authentication`、`user-feedback`、`vue-app-shell`。

当前变更 `openspec/changes/migrate-opspilot-platform-and-add-offline-eval/` 中的每个文件用途如下：

| 文件 | 用途 |
| --- | --- |
| `design.md` | 迁移和确定性 Eval v2 的设计决策与边界。 |
| `tasks.md` | 已完成和待验证的实施任务。 |
| `specs/offline-retrieval-evaluation/spec.md` | Eval v2 的 delta requirements。 |
| `specs/project-foundation/spec.md` | 品牌/工程基础的 delta requirements。 |

### OpenSpec 归档：每个历史文件

每个以下归档目录都包含其列出的**每一个文件**：`.openspec.yaml`（变更元数据）、`proposal.md`（变更目的和范围）、`design.md`（技术设计）、`tasks.md`（实施清单）、以及表中列出的 `specs/<能力>/spec.md`（该次变更对该能力的历史 delta specification）。这些文件均为追溯记录，不是当前实现的编辑目标；对应 WIKI 文件为 `docs/changes/archive/<同名目录>/index.md`。

| 归档目录 | 该目录内的每个 `specs/.../spec.md` |
| --- | --- |
| `2026-07-08-add-authorization-and-tenant-isolation` | api-and-sse-contracts, authorization-and-tenant-isolation, memory-repositories, user-authentication |
| `2026-07-08-add-user-authentication` | api-and-sse-contracts, memory-repositories, user-authentication |
| `2026-07-08-bootstrap-project-foundation` | project-foundation |
| `2026-07-08-configure-qwen-openai-provider` | qwen-openai-provider |
| `2026-07-08-define-api-and-sse-contracts` | api-and-sse-contracts, project-foundation |
| `2026-07-08-ignore-idea-files` | repo-hygiene |
| `2026-07-08-setup-sqlite-memory-repositories` | memory-repositories, project-foundation |
| `2026-07-08-standardize-docker-compose-startup` | docker-compose-startup, project-foundation |
| `2026-07-09-centralize-project-configuration` | docker-compose-startup, memory-repositories, milvus-vector-store, project-foundation, qwen-openai-provider |
| `2026-07-09-manage-chat-sessions` | api-and-sse-contracts, authorization-and-tenant-isolation, chat-sessions, memory-repositories |
| `2026-07-09-manage-knowledge-documents` | api-and-sse-contracts, authorization-and-tenant-isolation, knowledge-documents, memory-repositories, milvus-vector-store |
| `2026-07-09-provide-knowledge-retrieval-tool` | api-and-sse-contracts, authorization-and-tenant-isolation, knowledge-retrieval-tool, milvus-vector-store |
| `2026-07-09-run-document-indexing-jobs` | api-and-sse-contracts, authorization-and-tenant-isolation, document-indexing-jobs, knowledge-documents, memory-repositories, milvus-vector-store |
| `2026-07-09-setup-milvus-vector-store` | milvus-vector-store |
| `2026-07-09-stream-rag-chat` | api-and-sse-contracts, chat-sessions, knowledge-retrieval-tool, qwen-openai-provider, stream-rag-chat |
| `2026-07-10-active-alert-subscription-entry` | active-alert-subscription-entry |
| `2026-07-10-add-document-chunking-strategies` | api-and-sse-contracts, document-chunking-strategies, document-indexing-jobs, knowledge-base-ui, knowledge-documents, memory-repositories |
| `2026-07-10-add-readiness-and-config-checks` | runtime-readiness-checks |
| `2026-07-10-audit-agent-tool-calls` | agent-tool-call-audits, api-and-sse-contracts, memory-repositories, stream-rag-chat |
| `2026-07-10-automate-structured-diagnosis-cases` | automated-diagnosis-case-library, diagnosis-case-knowledge |
| `2026-07-10-build-aiops-diagnosis-ui` | aiops-diagnosis-ui |
| `2026-07-10-build-chat-experience` | chat-experience |
| `2026-07-10-build-knowledge-base-ui` | knowledge-base-ui |
| `2026-07-10-build-vue-app-shell` | vue-app-shell |
| `2026-07-10-complete-observability-baseline` | request-observability |
| `2026-07-10-configure-chat-prompt-skills` | api-and-sse-contracts, chat-experience, chat-prompt-skill-configuration, memory-repositories, stream-rag-chat |
| `2026-07-10-correct-runtime-readiness-checks` | runtime-readiness-checks |
| `2026-07-10-create-ecommerce-aiops-fixtures` | active-alert-subscription-entry, aiops-diagnosis-tasks, cls-log-generation, ecommerce-aiops-fixtures |
| `2026-07-10-create-readme` | docker-compose-startup, local-development-operations-guide, project-foundation |
| `2026-07-10-fix-knowledge-indexing-experience` | docker-compose-startup, document-indexing-jobs, knowledge-documents, qwen-openai-provider |
| `2026-07-10-generate-and-upload-cls-logs` | cls-log-generation |
| `2026-07-10-integrate-real-mcp-tools` | api-and-sse-contracts, real-mcp-tools, stream-rag-chat |
| `2026-07-10-knowledge-answer-citation-view` | knowledge-answer-citation-view, stream-rag-chat |
| `2026-07-10-localize-local-development-guides` | local-development-operations-guide |
| `2026-07-10-observability-baseline` | request-observability |
| `2026-07-10-persist-diagnosis-cases-to-knowledge-base` | diagnosis-case-knowledge |
| `2026-07-10-redesign-chinese-chatgpt-workspace` | aiops-diagnosis-ui, chat-experience, chinese-ai-workspace-experience, knowledge-base-ui, vue-app-shell |
| `2026-07-10-refactor-local-project-startup` | docker-compose-startup, frontend-end-to-end-validation, local-development-operations-guide, platform-installation-guides, project-foundation |
| `2026-07-10-refine-knowledge-document-layout` | knowledge-base-ui |
| `2026-07-10-run-aiops-diagnosis-tasks` | agent-tool-call-audits, aiops-diagnosis-tasks, api-and-sse-contracts, real-mcp-tools |
| `2026-07-10-store-aiops-evidence-and-reports` | aiops-diagnosis-tasks, aiops-evidence-chain, api-and-sse-contracts, memory-repositories |
| `2026-07-11-add-hybrid-knowledge-retrieval` | knowledge-retrieval-tool, milvus-vector-store |
| `2026-07-11-add-openspec-wiki` | openspec-wiki |
| `2026-07-11-add-reranked-knowledge-retrieval` | api-and-sse-contracts, chat-experience, knowledge-retrieval-tool, qwen-openai-provider |
| `2026-07-11-add-session-memory-modes` | api-and-sse-contracts, chat-experience, chat-memory-management, chat-sessions |
| `2026-07-11-adopt-standard-progressive-skills` | chat-experience, chat-prompt-skill-configuration, stream-rag-chat |
| `2026-07-11-auto-dismiss-global-feedback` | vue-app-shell |
| `2026-07-11-collect-user-feedback` | aiops-diagnosis-ui, api-and-sse-contracts, chat-experience, user-feedback |
| `2026-07-11-durable-background-job-runtime` | aiops-diagnosis-tasks, api-and-sse-contracts, background-job-runtime, document-indexing-jobs |
| `2026-07-11-expand-java-ecommerce-aiops-fixtures` | active-alert-subscription-entry, cls-log-generation, ecommerce-aiops-fixtures |
| `2026-07-11-extract-user-config-and-chat-assets` | api-and-sse-contracts, chat-prompt-skill-configuration, cls-log-generation, project-foundation, qwen-openai-provider, real-mcp-tools, shared-user-project-configuration, stream-rag-chat |
| `2026-07-11-fix-chat-turn-streaming` | chat-experience, stream-rag-chat |
| `2026-07-11-fix-knowledge-document-scrolling` | knowledge-base-ui |
| `2026-07-11-hide-empty-chat-placeholder` | chat-experience |
| `2026-07-11-improve-aiops-report-experience` | aiops-diagnosis-tasks, aiops-diagnosis-ui, aiops-evidence-chain |
| `2026-07-11-limit-qwen-embedding-batch-size` | qwen-openai-provider |
| `2026-07-11-manage-mcp-connections` | api-and-sse-contracts, mcp-connection-management, real-mcp-tools, vue-app-shell |
| `2026-07-11-move-chat-history-to-workspace-sidebar` | aiops-diagnosis-ui, chat-experience, chat-prompt-skill-configuration, vue-app-shell |
| `2026-07-11-pace-chat-typewriter-rendering` | chat-experience |
| `2026-07-11-polish-chat-and-aiops-interactions` | aiops-diagnosis-ui, aiops-evidence-chain, chat-experience, chat-prompt-skill-configuration |
| `2026-07-11-refine-chat-knowledge-aiops-ui` | aiops-diagnosis-ui, chat-experience, chat-prompt-skill-configuration, document-chunking-strategies, knowledge-documents |
| `2026-07-11-remove-compose-runtime-config` | docker-compose-startup, local-development-operations-guide |
| `2026-07-11-remove-project-config-from-git-history` | local-development-operations-guide, repo-hygiene, shared-user-project-configuration |
| `2026-07-11-show-retrieval-stage-ranks` | api-and-sse-contracts, knowledge-answer-citation-view, knowledge-retrieval-tool |
| `2026-07-11-use-positive-idf-bm25` | knowledge-retrieval-tool |

## 不在 GitHub 的本地文件

`config/project.json`、`config/user.project.json`、`docs/roadmap/agent-internship-optimization-roadmap.md`、`openspec/changes/migrate-opspilot-platform-and-add-offline-eval/proposal.md`、`openspec从0到1项目实战的提示词.md`、数据库、日志、缓存、`node_modules/` 和虚拟环境均应只留在本机，不纳入本索引。
