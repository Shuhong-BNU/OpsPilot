"""日志配置模块."""

from pathlib import Path
import sys

from loguru import logger

from app.config import config


def setup_logger():
    """配置日志系统

    按照 Loguru 最佳实践配置全局 logger：
    1. 移除默认处理器
    2. 添加控制台输出（带颜色）
    3. 添加文件输出（按天轮转，自动压缩，异步写入）
    """
    # 移除默认处理器
    logger.remove()

    # 添加控制台输出（带颜色格式）
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>.<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        level="DEBUG" if config.debug else "INFO",
        colorize=True,
        backtrace=True,  # 显示完整异常栈信息
        diagnose=config.debug,  # Debug 模式下显示变量值
    )

    Path("logs").mkdir(parents=True, exist_ok=True)

    file_handler_options = {
        "sink": "logs/app_{time:YYYY-MM-DD}.log",
        "rotation": "00:00",
        "retention": "7 days",
        "compression": "zip",
        "encoding": "utf-8",
        "enqueue": True,
        "backtrace": True,
        "diagnose": True,
        "level": "INFO",
        "format": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}.{function}:{line} | {message}",
    }

    try:
        logger.add(**file_handler_options)
    except PermissionError:
        # Windows 某些受限环境下 multiprocessing 队列不可用，回退为同步写入。
        file_handler_options["enqueue"] = False
        logger.add(**file_handler_options)

setup_logger()
