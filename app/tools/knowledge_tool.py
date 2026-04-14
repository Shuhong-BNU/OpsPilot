"""知识检索工具 - 从混合检索链路中检索相关信息."""

from time import perf_counter
from typing import List, Tuple

from langchain_core.documents import Document
from langchain_core.tools import tool
from loguru import logger

from app.services.request_context_service import get_request_context
from app.services.retrieval_service import retrieval_service
from app.services.session_service import session_service


@tool(response_format="content_and_artifact")
def retrieve_knowledge(query: str) -> Tuple[str, List[Document]]:
    """从知识库中检索相关信息来回答问题
    
    当用户的问题涉及专业知识、文档内容或需要参考资料时，使用此工具。
    
    Args:
        query: 用户的问题或查询
        
    Returns:
        Tuple[str, List[Document]]: (格式化的上下文文本, 原始文档列表)
    """
    started_at = perf_counter()
    context = get_request_context()
    try:
        logger.info(f"知识检索工具被调用: query='{query}'")

        docs, trace = retrieval_service.hybrid_search(query)
        if not docs:
            logger.warning("未检索到相关文档")
            return "没有找到相关信息。", []

        # 格式化文档为上下文
        content = retrieval_service.format_docs(docs)
        latency_ms = int((perf_counter() - started_at) * 1000)
        session_service.log_tool_call(
            session_id=context.session_id,
            workflow_run_id=context.workflow_run_id,
            tool_name="retrieve_knowledge",
            status="success",
            latency_ms=latency_ms,
            input_payload=query,
            output_payload=retrieval_service.summarize_trace(trace),
        )
        logger.info(f"检索到 {len(docs)} 个相关文档")
        return content, docs

    except Exception as e:
        logger.error(f"知识检索工具调用失败: {e}")
        latency_ms = int((perf_counter() - started_at) * 1000)
        session_service.log_tool_call(
            session_id=context.session_id,
            workflow_run_id=context.workflow_run_id,
            tool_name="retrieve_knowledge",
            status="failed",
            latency_ms=latency_ms,
            input_payload=query,
            error_message=str(e),
        )
        return f"检索知识时发生错误: {str(e)}", []
