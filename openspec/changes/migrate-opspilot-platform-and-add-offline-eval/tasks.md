## 1. 迁移与品牌

- [x] 1.1 迁移 Monorepo 技术底座到既有 OpsPilot 仓库根目录。
- [x] 1.2 将 Python、npm、服务、配置、文档和运行命令统一命名为 OpsPilot。
- [x] 1.3 保留旧 SOP 语料并清理旧 latest Eval artifact。

## 2. Eval

- [x] 2.1 实现通过生产 `KnowledgeRetrievalTool` 的确定性离线 adapter。
- [x] 2.2 增加 Hit@1、Hit@3、MRR、Recall@3 与 stage evidence 输出。
- [x] 2.3 为离线 Eval 适配器添加最小单元测试。
- [x] 2.4 同步中英文 Eval 文档与求职优化路线图。

## 3. 验证

- [x] 3.1 执行 Python 源码编译和旧名称/版本审计。
- [ ] 3.2 在 CLS SDK native dependency 可安装的环境执行完整 `uv sync`、pytest、Ruff 和 Pyright。
- [ ] 3.3 执行 Node 环境中的前端 typecheck、test、build 和文档构建。
- [ ] 3.4 执行 `openspec validate --all`。
