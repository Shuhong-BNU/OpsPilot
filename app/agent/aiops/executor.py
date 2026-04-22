"""
Executor 节点：执行单个步骤。
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_qwq import ChatQwen
from langgraph.prebuilt import ToolNode
from loguru import logger

from app.agent.mcp_client import get_mcp_client_with_retry
from app.config import config
from app.tools import get_current_time, retrieve_knowledge

from .state import PlanExecuteState


async def executor(state: PlanExecuteState) -> dict[str, Any]:
    """执行计划中的下一步。"""
    logger.info("=== Executor：执行步骤 ===")

    plan = state.get("plan", [])
    if not plan:
        logger.info("计划为空，跳过执行")
        return {}

    task = plan[0]
    logger.info(f"当前任务: {task}")

    local_tools = [get_current_time, retrieve_knowledge]
    try:
        mcp_client = await get_mcp_client_with_retry()
        mcp_tools = await mcp_client.get_tools()
        logger.info(f"可用工具数量: 本地 {len(local_tools)} + MCP {len(mcp_tools)}")
    except Exception as exc:
        logger.warning(f"获取 MCP 工具失败，降级为仅本地工具: {exc}")
        mcp_tools = []

    all_tools = local_tools + mcp_tools

    try:
        llm = ChatQwen(
            model=config.rag_model,
            api_key=config.dashscope_api_key,
            temperature=0,
        )
        llm_with_tools = llm.bind_tools(all_tools)
        tool_node = ToolNode(all_tools)

        messages = [
            SystemMessage(
                content=(
                    "你是 AIOps 工作流中的 Executor，负责执行当前单个步骤。"
                    "如果有工具可用，请优先基于工具结果回答；如果工具调用失败，要明确说明失败原因。"
                )
            ),
            HumanMessage(content=f"请执行以下任务：{task}"),
        ]

        llm_response = await llm_with_tools.ainvoke(messages)
        if getattr(llm_response, "tool_calls", None):
            logger.info(f"检测到 {len(llm_response.tool_calls)} 个工具调用")
            messages.append(llm_response)
            tool_messages = await tool_node.ainvoke({"messages": messages})
            messages.extend(tool_messages["messages"])
            final_response = await llm_with_tools.ainvoke(messages)
            result = final_response.content if hasattr(final_response, "content") else str(final_response)
        else:
            logger.info("未检测到工具调用，直接使用模型结果")
            result = llm_response.content if hasattr(llm_response, "content") else str(llm_response)

        logger.info(f"步骤执行完成，结果长度: {len(result)}")
        return {
            "plan": plan[1:],
            "past_steps": [(task, result)],
        }
    except Exception as exc:
        logger.error(f"执行步骤失败: {exc}", exc_info=True)
        return {
            "plan": plan[1:],
            "past_steps": [(task, f"执行失败: {exc}")],
        }
