"""时间工具 - 获取当前时间信息."""

from datetime import datetime
from time import perf_counter
from zoneinfo import ZoneInfo

from langchain_core.tools import tool
from loguru import logger

from app.services.request_context_service import get_request_context
from app.services.session_service import session_service


@tool
def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """获取当前时间
    
    当用户询问"现在几点"、"今天星期几"、"今天日期"等时间相关问题时，使用此工具。
    
    Args:
        timezone: 时区，默认为 Asia/Shanghai（北京时间）
        
    Returns:
        str: 格式化的当前时间信息
    """
    started_at = perf_counter()
    context = get_request_context()
    try:
        # 获取指定时区的当前时间
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)

        # 返回格式化的日期时间字符串
        output = now.strftime('%Y-%m-%d %H:%M:%S')
        session_service.log_tool_call(
            session_id=context.session_id,
            workflow_run_id=context.workflow_run_id,
            tool_name="get_current_time",
            status="success",
            latency_ms=int((perf_counter() - started_at) * 1000),
            input_payload=timezone,
            output_payload=output,
        )
        return output

    except Exception as e:
        logger.error(f"时间查询工具调用失败: {e}")
        session_service.log_tool_call(
            session_id=context.session_id,
            workflow_run_id=context.workflow_run_id,
            tool_name="get_current_time",
            status="failed",
            latency_ms=int((perf_counter() - started_at) * 1000),
            input_payload=timezone,
            error_message=str(e),
        )
        return f"获取时间失败: {str(e)}"
