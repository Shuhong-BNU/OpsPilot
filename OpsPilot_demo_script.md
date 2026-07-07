# OpsPilot 演示脚本

本手册用于简历展示、面试讲解和录屏演示，目标是稳定复现 OpsPilot 的核心能力，而不是追求一次性跑完所有功能。

## 启动前检查

1. 确认 `.env` 中已配置真实 `DASHSCOPE_API_KEY`。
2. 确认 `DASHSCOPE_MODEL / DASHSCOPE_EMBEDDING_MODEL / DASHSCOPE_RERANK_MODEL / RAG_MODEL` 已按当前环境填写。
3. 确认 Docker Desktop 已启动，Milvus 可用。
4. 执行 `.\start-windows.bat`，等待脚本输出：
   - `Listen address: http://0.0.0.0:9900`
   - `Browser URL: http://localhost:9900`
5. 打开 `http://localhost:9900`。

## 演示使用建议

- 优先演示 `1 条主案例 + 1 条备用案例`，不要为了“全展示”把节奏拖慢。
- 如果现场稳定性优先，尽量使用和知识库文件强相关的问题，结果会更可控。
- 如果时间有限，最少覆盖 `系统状态 -> knowledge_qa -> aiops_diagnosis` 三段，就足够讲清项目价值。

## 推荐演示顺序

### 1. 系统状态面板

- 登录前先说明：`0.0.0.0` 是服务监听地址，真正给浏览器访问的是 `localhost:9900`。
- 登录 `viewer / viewer123` 后，点击右上角 `系统状态`。
- 重点讲：
  - 当前模型配置
  - DashScope Key 只做掩码展示
  - SQLite / Milvus / MCP 服务是否就绪
  - 项目不是把原始日志暴露给用户，而是做了结构化状态呈现

### 2. smalltalk

- 主提示词：`你好`
- 备用提示词：
  - `你是谁？`
  - `早上好，简单介绍一下你自己`
- 预期现象：
  - 快速返回简单问候
  - 执行轨迹里出现 `意图分流 -> smalltalk`
- 讲解要点：
  - 规则优先分流
  - 简单请求不走重型链路

### 3. simple_qa

- 主提示词：`北京在哪里`
- 备用提示词：
  - `北京是中国的首都吗？`
  - `什么是 HTTP 状态码 404？`
- 预期现象：
  - 正常直接回答
  - 执行轨迹显示 `simple_qa`
- 讲解要点：
  - 普通知识问答走轻链路
  - 响应时延比 RAG/AIOps 更短

### 4. stream chat

- 切换到底部 `流式` 模式
- 主提示词：`请用三点概括什么是 CPU 高负载`
- 备用提示词：
  - `请用两句话解释什么是慢响应告警`
  - `请把内存高负载的常见现象总结成三条`
- 预期现象：
  - 回答逐步流式输出
  - 执行轨迹里能看到路由与完成事件
- 讲解要点：
  - SSE 流式对话已打通
  - 面向前端体验做了实时输出

### 5. knowledge_qa

- 先确认已上传知识库文档；如果没有，使用 `operator / operator123` 上传 `aiops-docs/*.md`
- 推荐命中文档：
  - `cpu_high_usage.md`
  - `slow_response.md`
  - `disk_high_usage.md`
  - `memory_high_usage.md`
  - `service_unavailable.md`
- 主提示词：
  - `根据知识库，CPU 高负载常见排查步骤有哪些？`
  - `结合文档解释慢响应告警一般如何定位`
- 备用提示词：
  - `根据知识库，磁盘高负载常见原因和排查顺序是什么？`
  - `结合文档总结内存高负载的典型现象与排查重点`
  - `如果服务不可用，知识库建议先检查哪些项？`
- 预期现象：
  - 返回基于资料的回答
  - 执行轨迹出现 `RAG 检索`
  - 能看到 `dense / sparse / fusion / rerank` 的摘要
- 讲解要点：
  - 混合检索而非单一路径召回
  - 前端不展示原始后端日志，而展示结构化检索 trace

### 6. auth boundary

- 保持 `viewer` 角色，点击右上角 `AI Ops`
- 预期现象：
  - 前端直接提示：`当前角色为 viewer，仅支持聊天与知识问答，不支持 AIOps 诊断`
  - 不再反复触发 `403`
- 讲解要点：
  - 前端做体验层防误触
  - 后端仍保留真实权限校验

### 7. aiops_diagnosis

- 切换账号为 `operator / operator123`
- 点击右上角 `AI Ops`
- 场景口播示例：
  - `假设现在收到一条 CPU 高负载告警，我不手工翻日志，直接让系统自动走一轮诊断。`
  - `假设线上接口大量超时，我触发 AIOps 链路，让它自己规划排查步骤并输出报告。`
- 预期现象：
  - 聊天区展示最终诊断报告
  - `执行轨迹` 按顺序出现 `status / plan / step_complete / report / complete`
- 讲解要点：
  - Plan-Execute-Replan 闭环已打通
  - MCP 工具调用支撑日志与监控排查
  - 诊断过程、结果与会话状态可追踪

### 8. unsupported

- 主提示词：`帮我写一封情书`
- 备用提示词：
  - `帮我写一首情诗`
  - `给女朋友写一段生日祝福`
- 预期现象：
  - 明确拒答
  - 执行轨迹显示 `unsupported`
- 讲解要点：
  - 项目定义了职责边界
  - 不把无关请求强行塞进运维助手能力里

## 知识库问答范例池

### CPU 高负载

- `根据知识库，CPU 高负载常见排查步骤有哪些？`
- `如果 CPU 长时间打满，通常先看哪些指标？`
- `结合文档解释 CPU 高负载时为什么要先区分系统态和用户态。`

### 慢响应

- `结合文档解释慢响应告警一般如何定位`
- `根据知识库，慢响应场景的排查顺序通常是什么？`
- `如果接口 RT 持续升高，应该先确认应用层还是下游依赖？`

### 磁盘高负载

- `根据知识库，磁盘高负载常见原因和排查顺序是什么？`
- `磁盘空间告急时，知识库建议先做哪些止血动作？`
- `如果磁盘 IO 持续很高，通常先排查哪些进程或目录？`

### 内存高负载

- `结合文档总结内存高负载的典型现象与排查重点`
- `如果怀疑内存泄漏，知识库建议先看哪些信息？`
- `如何区分内存短时突增和持续性内存异常？`

### 服务不可用

- `如果服务不可用，知识库建议先检查哪些项？`
- `遇到服务 5xx 或完全不可达时，第一轮排查应该覆盖哪些层面？`
- `根据文档，服务不可用时应该如何快速缩小故障范围？`

## 不同时长的演示组合

### 3 分钟版

- `系统状态面板`：先交代技术栈与依赖状态。
- `knowledge_qa`：演示 `根据知识库，CPU 高负载常见排查步骤有哪些？`
- `aiops_diagnosis`：展示自动规划和诊断报告。

### 5 分钟版

- `系统状态面板`
- `stream chat`：演示流式输出体验。
- `knowledge_qa`：演示结构化检索 trace。
- `auth boundary`：补一段角色权限控制。
- `aiops_diagnosis`

### 8-10 分钟版

- `系统状态面板`
- `smalltalk / simple_qa`：说明轻链路与重链路分流。
- `stream chat`
- `knowledge_qa`
- `auth boundary`
- `aiops_diagnosis`
- `unsupported`：最后用边界能力收尾。

## 面试讲解建议

- 先讲定位：`OpsPilot 是基于 RAG 与 MCP 的智能运维助手`
- 再讲分流：`先做意图识别，再决定直答 / RAG / AIOps`
- 再讲工程化：
  - JWT + 角色权限
  - SQLite 持久化会话与工作流
  - 混合检索 + rerank
  - 测试与 metrics
  - 前端状态面板与执行轨迹
- 最后强调边界：
  - 这是近真实、可复现、可讲清楚的数据闭环
  - 不是伪装成真实生产平台的夸大叙事


## 工程亮点口播

这段适合在产品演示结束后补充 60-90 秒，不替代完整面试讲解。

> 我没有只停在“这个 Demo 能回答问题”。后续我为 Retrieval 链路补了固定 10-case 离线 Eval，直接评估 `Milvus dense + SQLite FTS5 sparse + RRF + lightweight rerank`。Baseline v1 的 Hit@3 已经是 1.000，但 trace 显示 sparse relevant hit 是 0/10，说明名义上的 Hybrid 实际没有 sparse 贡献。
>
> 我继续做只读诊断，确认 FTS5 有 21 条真实 chunk、SQL mapping 正常，问题主要来自中文 tokenizer 限制和 multi-token AND 查询过严。随后用同一 dataset 做 AND vs quoted OR 单变量实验，OR 让 sparse relevant hit 提升到 4/10，再做最小 query-builder 修复，建立 Baseline v1.1，在项目内 10 条固定样例上 MRR 从 0.95 提升到 1.00。
>
> 这条链路说明项目不是只靠演示，而是有 baseline、诊断、单变量实验、修复、复测和 PR review 的工程闭环。

完整面试讲法见 [OpsPilot_interview_handbook.md](./OpsPilot_interview_handbook.md)。
