"""
Replanner 节点：重新规划或生成最终响应。
"""

from __future__ import annotations

from textwrap import dedent
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_qwq import ChatQwen
from loguru import logger
from pydantic import BaseModel, Field

from app.agent.mcp_client import get_mcp_client_with_retry
from app.config import config
from app.tools import get_current_time, retrieve_knowledge

from .state import PlanExecuteState
from .utils import format_tools_description


class Response(BaseModel):
    response: str = Field(description="对用户的最终回答")


class Act(BaseModel):
    action: str = Field(description="continue / replan / respond")
    new_steps: list[str] = Field(default_factory=list, description="重新规划后的剩余步骤")


replanner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            dedent(
                """
                你是 AIOps 工作流中的 Replanner，负责判断是否继续执行、重排步骤或直接回答。

                可用工具：
                {tools_description}

                决策原则：
                1. 信息足够时优先 respond。
                2. 当前计划仍合理时选择 continue。
                3. 只有计划明显失效时才选择 replan。
                4. 已执行步骤过多时，不要继续扩张计划。
                """
            ).strip(),
        ),
        ("placeholder", "{messages}"),
    ]
)

response_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            dedent(
                """
                你是 AIOps 工作流的最终报告生成器。
                请基于已执行步骤与结果，输出结构化 Markdown 响应。
                要求诚实，不要编造不存在的工具结果。
                """
            ).strip(),
        ),
        ("placeholder", "{messages}"),
    ]
)


async def replanner(state: PlanExecuteState) -> dict[str, Any]:
    """决定继续执行还是生成最终响应。"""
    logger.info("=== Replanner：重新规划 ===")

    input_text = state.get("input", "")
    plan = state.get("plan", [])
    past_steps = state.get("past_steps", [])

    logger.info(f"剩余计划步骤: {len(plan)}")
    logger.info(f"已执行步骤: {len(past_steps)}")

    if len(past_steps) >= 8:
        logger.warning("已执行步骤过多，强制生成最终响应")
        llm = ChatQwen(model=config.rag_model, api_key=config.dashscope_api_key, temperature=0)
        return await _generate_response(state, llm)

    local_tools = [get_current_time, retrieve_knowledge]
    try:
        mcp_client = await get_mcp_client_with_retry()
        mcp_tools = await mcp_client.get_tools()
        logger.info(f"可用工具数量: 本地 {len(local_tools)} + MCP {len(mcp_tools)}")
    except Exception as exc:
        logger.warning(f"获取工具列表失败，降级为仅本地工具: {exc}")
        mcp_tools = []

    tools_description = format_tools_description(local_tools + mcp_tools) or "- 无可用工具描述"

    llm = ChatQwen(model=config.rag_model, api_key=config.dashscope_api_key, temperature=0)

    if not plan:
        logger.info("计划执行完成，生成最终响应")
        return await _generate_response(state, llm)

    steps_summary = "\n".join(
        f"步骤: {step}\n结果: {result[:300]}..." for step, result in past_steps
    ) or "暂无已执行步骤"

    try:
        replanner_chain = replanner_prompt | llm.with_structured_output(Act)
        act = await replanner_chain.ainvoke(
            {
                "messages": [
                    ("user", f"原始任务: {input_text}"),
                    ("user", f"已执行步骤:\n{steps_summary}"),
                    ("user", f"剩余步骤: {', '.join(plan)}"),
                    ("user", f"当前已执行 {len(past_steps)} 个步骤，请优先评估是否可以直接回答。"),
                ],
                "tools_description": tools_description,
            }
        )

        action = act.action if isinstance(act, Act) else act.get("action", "continue")
        new_steps = act.new_steps if isinstance(act, Act) else act.get("new_steps", [])
        logger.info(f"Replanner 决策: {action}")

        if action == "respond":
            logger.info("决定生成最终响应")
            return await _generate_response(state, llm)

        if action == "replan":
            if len(past_steps) >= 5:
                logger.warning("已执行步骤较多，禁止继续扩张计划，改为直接响应")
                return await _generate_response(state, llm)

            trimmed_steps = [step.strip() for step in new_steps if step and step.strip()]
            if not trimmed_steps:
                logger.warning("replan 未返回有效步骤，继续沿用原计划")
                return {}

            if len(trimmed_steps) > len(plan):
                logger.warning(
                    f"新步骤数 {len(trimmed_steps)} > 剩余步骤数 {len(plan)}，强制截断为 {len(plan)} 个步骤"
                )
                trimmed_steps = trimmed_steps[: len(plan)]

            logger.info(f"决定调整计划，新步骤数量: {len(trimmed_steps)}")
            return {"plan": trimmed_steps}

        logger.info("决定继续执行当前计划")
        return {}
    except Exception as exc:
        logger.error(f"重新规划失败: {exc}, 继续执行剩余计划")
        return {}


async def _generate_response(state: PlanExecuteState, llm: ChatQwen) -> dict[str, Any]:
    """生成最终响应。"""
    logger.info("生成最终响应...")

    input_text = state.get("input", "")
    past_steps = state.get("past_steps", [])

    execution_history = "\n\n".join(
        f"### 步骤: {step}\n**结果:**\n{result}" for step, result in past_steps
    ) or "暂无执行结果"

    try:
        response_gen = response_prompt | llm.with_structured_output(Response)
        response_obj = await response_gen.ainvoke(
            {
                "messages": [
                    ("user", f"原始任务: {input_text}"),
                    ("user", f"执行历史:\n{execution_history}"),
                    ("user", "请基于以上信息生成最终响应。"),
                ]
            }
        )
        final_response = response_obj.response if isinstance(response_obj, Response) else response_obj.get("response", "")
        logger.info(f"最终响应生成完成，长度: {len(final_response)}")
        return {"response": final_response}
    except Exception as exc:
        logger.error(f"生成响应失败: {exc}")
        return {
            "response": (
                "# 任务执行结果\n\n"
                f"## 原始任务\n{input_text}\n\n"
                "## 执行步骤\n"
                f"{_format_simple_steps(past_steps)}\n\n"
                "## 说明\n由于系统异常，未能生成更完整的最终响应。"
            )
        }


def _format_simple_steps(past_steps: list[tuple[str, str]]) -> str:
    if not past_steps:
        return "无"

    formatted = []
    for index, (step, result) in enumerate(past_steps, start=1):
        preview = result[:200] + "..." if len(result) > 200 else result
        formatted.append(f"{index}. **{step}**\n   {preview}")
    return "\n".join(formatted)
