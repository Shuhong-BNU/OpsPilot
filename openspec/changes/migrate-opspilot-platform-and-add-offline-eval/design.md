## Context

迁移后的项目复用 `KnowledgeRetrievalTool`，该工具执行权限过滤、向量与 BM25L 召回、RRF 融合和 rerank 结果组装。真实路径还依赖 Milvus、远程 embedding 与 Qwen rerank，不能作为每次 CI 的可靠前提。

## Decisions

### 用确定性 adapter 运行生产检索编排

离线 Eval 只替换外部边界：以 hash-token embedding 代替远程 embedding、以内存语料 store 代替 Milvus、以 token overlap reranker 代替 Qwen。生产 `KnowledgeRetrievalTool`、范围过滤、BM25L、RRF、引用与分阶段 rank 字段保持不变。

这证明的是编排和回归行为，不宣称真实模型或 Milvus 的线上质量、延迟或成本。线上 integration eval 必须使用独立环境、真实服务和单独报告。

### 历史 baseline 不与 v2 直接比较

v1/v1.1 的数据和报告来自迁移前的旧 retrieval 实现，保留其 provenance，但不重写。旧 latest artifact 带有旧代码路径和绝对本机路径，删除以避免混淆。

### 将产品标识统一为 OpsPilot

包名采用 `opspilot`，服务名采用 `opspilot-backend`，npm scope 采用 `@opspilot/*`。这是一项跨模块迁移，因此同时更新源码、测试、锁文件、配置、文档和 OpenSpec 记录。

## Risks

- 离线 adapter 可能与线上模型排序不同：通过明确报告边界和后续线上 integration eval 处理。
- 大规模目录替换可能留下旧标识：通过全仓字符串审计、编译与健康契约测试处理。
- CLS SDK 的原生依赖可能阻止本机全量安装：不降低生产依赖要求，记录为本机验证环境限制。
