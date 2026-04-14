"""FastAPI 应用入口

主应用程序，配置路由、中间件、静态文件等
"""

from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.config import config
from loguru import logger
from app.api import aiops, auth, chat, file, health, metrics, sessions
from app.core.milvus_client import milvus_manager
from app.services.auth_service import auth_service
from app.services.database_service import database_service
from app.services.metrics_service import metrics_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("=" * 60)
    logger.info(f"🚀 {config.app_name} v{config.app_version} 启动中...")
    logger.info(f"📝 环境: {'开发' if config.debug else '生产'}")
    logger.info(f"🌐 监听地址: http://{config.host}:{config.port}")
    logger.info(f"📚 API 文档: http://{config.host}:{config.port}/docs")

    database_service.initialize()
    auth_service.initialize()

    # 连接 Milvus
    logger.info("🔌 正在连接 Milvus...")
    try:
        milvus_manager.connect()
        logger.info("✅ Milvus 连接成功")
    except Exception as exc:
        logger.warning(f"⚠️ Milvus 初始化失败，RAG 能力将在运行时按需重试: {exc}")
    
    logger.info("=" * 60)
    
    yield
    
    # 关闭时执行
    logger.info("🔌 正在关闭 Milvus 连接...")
    milvus_manager.close()
    logger.info(f"👋 {config.app_name} 关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description=config.app_description,
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, tags=["健康检查"])
app.include_router(metrics.router, tags=["监控"])
app.include_router(auth.router, prefix="/api", tags=["鉴权"])
app.include_router(chat.router, prefix="/api", tags=["对话"])
app.include_router(sessions.router, prefix="/api", tags=["会话管理"])
app.include_router(file.router, prefix="/api", tags=["文件管理"])
app.include_router(aiops.router, prefix="/api", tags=["AIOps智能运维"])

# 挂载静态文件
static_dir = "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    started_at = perf_counter()
    response = await call_next(request)
    metrics_service.increment("http_request_total")
    metrics_service.observe("http_request_latency", int((perf_counter() - started_at) * 1000))
    return response

@app.get("/")
async def root():
    """返回首页"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": f"Welcome to {config.app_name} API",
        "version": config.app_version,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="info"
    )
