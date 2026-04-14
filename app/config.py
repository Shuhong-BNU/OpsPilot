"""配置管理模块."""

from typing import Any, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用配置
    app_name: str = "OpsPilot"
    app_title: str = "基于 RAG 与 MCP 的智能运维助手"
    app_description: str = (
        "OpsPilot 面向企业运维场景，提供知识增强问答、意图路由分流、"
        "AIOps 智能诊断与工具调用能力，帮助用户完成从问题识别、信息检索到排障建议生成的闭环。"
    )
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 9900

    # 持久化与鉴权
    database_path: str = "./data/opspilot.db"
    jwt_secret: str = "opspilot-dev-secret"
    jwt_expire_minutes: int = 720
    password_hash_iterations: int = 120000
    default_viewer_username: str = "viewer"
    default_viewer_password: str = "viewer123"
    default_operator_username: str = "operator"
    default_operator_password: str = "operator123"
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"

    # DashScope 配置
    dashscope_api_key: str = ""  # 默认空字符串，实际使用需从环境变量加载
    dashscope_model: str = "qwen-max"
    dashscope_embedding_model: str = "text-embedding-v4"  # v4 支持多种维度（默认 1024）

    # Milvus 配置
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_timeout: int = 10000  # 毫秒

    # RAG 配置
    rag_top_k: int = 3
    rag_model: str = "qwen-max"  # 使用快速响应模型，不带扩展思考
    dense_top_k: int = 6
    sparse_top_k: int = 6
    hybrid_top_k: int = 4
    rerank_top_k: int = 3

    # 文档分块配置
    chunk_max_size: int = 800
    chunk_overlap: int = 100

    # MCP 服务配置
    mcp_cls_transport: str = "streamable-http"
    mcp_cls_url: str = "http://localhost:8003/mcp"
    mcp_monitor_transport: str = "streamable-http"
    mcp_monitor_url: str = "http://localhost:8004/mcp"

    # 监控开关
    metrics_enabled: bool = True

    @property
    def mcp_servers(self) -> Dict[str, Dict[str, Any]]:
        """获取完整的 MCP 服务器配置"""
        return {
            "cls": {
                "transport": self.mcp_cls_transport,
                "url": self.mcp_cls_url,
            },
            "monitor": {
                "transport": self.mcp_monitor_transport,
                "url": self.mcp_monitor_url,
            }
        }


# 全局配置实例
config = Settings()
