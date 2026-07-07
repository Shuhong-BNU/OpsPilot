# MCP Servers

为 AIOps 智能诊断提供日志查询和监控数据工具。

## 📚 服务列表

### CLS Server (`cls_server.py`)
**日志查询服务** - 端口 8003

**核心工具：**
- `get_current_timestamp` - 获取当前时间戳
- `get_region_code_by_name` - 根据地区名称查询地区代码
- `get_topic_info_by_name` - 查询日志主题
- `search_topic_by_service_name` - 根据服务名称搜索日志主题
- `search_log` - 日志搜索

### Monitor Server (`monitor_server.py`)
**监控数据服务** - 端口 8004

**核心工具：**
- `query_cpu_metrics` - CPU 使用率查询
- `query_memory_metrics` - 内存使用查询

## 🚀 快速开始

### 安装依赖
```bash
pip install fastmcp
```

### 启动服务

**方式一：使用 Makefile（推荐）**
```bash
make start        # 启动 CLS + Monitor MCP + FastAPI
make stop         # 停止所有服务
make status-mcp   # 查看 MCP 服务状态

make start-cls      # 只启动 CLS MCP 服务
make start-monitor  # 只启动 Monitor MCP 服务
```

**方式二：手动启动**
```bash
python mcp_servers/cls_server.py
python mcp_servers/monitor_server.py
```

## 💡 使用示例

### AIOps 诊断场景

```
用户: data-sync-service 出现告警，请排查

Agent 自动执行:
1. search_topic_by_service_name(service_name="data-sync-service") → 查找服务对应的日志 topic
2. get_current_timestamp() → 获取当前毫秒时间戳
3. search_log(topic_id="topic-001", start_time=..., end_time=..., query="level:ERROR") → 查询错误日志
4. query_cpu_metrics(service_name="data-sync-service") → CPU 趋势分析
5. query_memory_metrics(service_name="data-sync-service") → 内存趋势分析
6. 综合分析 → 生成诊断报告和修复建议
```

### 工具参数示例

**按服务查找日志 Topic：**
```python
search_topic_by_service_name(
    service_name="data-sync-service",
    fuzzy=True
)
```

**搜索错误日志：**
```python
current_ts = get_current_timestamp()
start_ts = current_ts - (15 * 60 * 1000)

search_log(
    topic_id="topic-001",
    start_time=start_ts,
    end_time=current_ts,
    query="level:ERROR",
    limit=100
)
```

**查询 CPU 指标：**
```python
query_cpu_metrics(
    service_name="data-sync-service",
    start_time="2026-02-14 02:00:00",
    interval="1m"
)
```

**查询内存指标：**
```python
query_memory_metrics(
    service_name="data-sync-service",
    start_time="2026-02-14 02:00:00",
    interval="1m"
)
```

## 🧭 Mock / Real 边界

当前 MCP 协议链路、Server 进程和工具定义是真实实现；AIOps 可以通过 MCP client 获取工具并发起调用。

默认返回的日志数据、CPU 指标和内存指标是可复现 Mock 数据。仓库默认没有接入生产 Prometheus、真实腾讯云 CLS、MySQL 或云监控。接入真实 API 时，应在现有 server 文件中替换数据源适配层，并保留工具入参和返回结构的兼容性。

## 🔧 高级配置

### 接入真实 API

当前返回模拟数据。接入真实 API 步骤：

**腾讯云 CLS：**
```bash
# 安装 SDK
pip install tencentcloud-sdk-python

# 配置环境变量
export TENCENTCLOUD_SECRET_ID="your-id"
export TENCENTCLOUD_SECRET_KEY="your-key"

# 在 cls_server.py 中集成
from tencentcloud.cls.v20201016 import cls_client
```

**其他监控系统：**
- Prometheus
- Grafana
- 云监控（腾讯云/阿里云/AWS）
- 自建监控平台

### 自定义 Mock 数据

修改各 Server 文件中的数据生成逻辑，模拟实际场景。

## 📚 参考资料

- [FastMCP 文档](https://github.com/jlowin/fastmcp)
- [MCP 协议](https://modelcontextprotocol.io/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [主项目 README](../README.md)

---

**注意**: 当前版本返回模拟数据，生产环境需配置真实 API。
