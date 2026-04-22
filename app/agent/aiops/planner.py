"""
Planner 节点：制定执行计划。
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


class Plan(BaseModel):
    """计划输出结构。"""

    steps: list[str] = Field(description="按顺序执行的步骤列表。")


planner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            dedent(
                """
                你是 AIOps 诊断工作流中的 Planner，负责把复杂问题拆成可执行步骤。

                可用工具如下：
                {tools_description}

                如有知识库经验，请优先参考：
                {experience_context}

                输出要求：
                1. 计划尽量简洁，优先保留关键步骤。
                2. 每一步都要能独立执行。
                3. 不要编造工具。
                4. 步骤应贴近排障实际顺序。
                """
            ).strip(),
        ),
        ("placeholder", "{messages}"),
    ]
)


async def planner(state: PlanExecuteState) -> dict[str, Any]:
    """根据输入生成执行计划。"""
    logger.info("=== Planner：制定执行计划 ===")

    input_text = state.get("input", "")
    logger.info(f"用户输入: {input_text}")

    experience_context = ""
    try:
        logger.info("查询内部文档，寻找相关经验...")
        context_str = await retrieve_knowledge.ainvoke({"query": input_text})
        if context_str and context_str.strip():
            experience_context = context_str
            logger.info(f"找到相关经验文档，长度: {len(experience_context)}")
        else:
            logger.info("未找到相关经验文档")
    except Exception as exc:
        logger.warning(f"查询内部文档失败: {exc}")

    local_tools = [get_current_time, retrieve_knowledge]

    try:
        mcp_client = await get_mcp_client_with_retry()
        mcp_tools = await mcp_client.get_tools()
        logger.info(f"可用工具数量: 本地 {len(local_tools)} + MCP {len(mcp_tools)}")
    except Exception as exc:
        logger.warning(f"获取 MCP 工具失败，降级为仅本地工具: {exc}")
        mcp_tools = []

    tools_description = format_tools_description(local_tools + mcp_tools) or "- 无可用工具描述"
    formatted_experience_context = (
        "以下为检索到的相关经验，请参考其方法与步骤制定计划：\n\n" + experience_context
        if experience_context
        else "未检索到可直接复用的经验文档。"
    )

    try:
        llm = ChatQwen(
            model=config.rag_model,
            api_key=config.dashscope_api_key,
            temperature=0,
        )
        planner_chain = planner_prompt | llm.with_structured_output(Plan)
        plan_result = await planner_chain.ainvoke(
            {
                "messages": [("user", input_text)],
                "tools_description": tools_description,
                "experience_context": formatted_experience_context,
            }
        )

        plan_steps = plan_result.steps if isinstance(plan_result, Plan) else plan_result.get("steps", [])
        plan_steps = [step.strip() for step in plan_steps if step and step.strip()]

        if not plan_steps:
            raise ValueError("Planner 未生成有效步骤")

        logger.info(f"计划已生成，共 {len(plan_steps)} 个步骤")
        for index, step in enumerate(plan_steps, start=1):
            logger.info(f"  步骤{index}: {step}")

        return {"plan": plan_steps}
    except Exception as exc:
        logger.error(f"生成计划失败: {exc}", exc_info=True)
        return {
            "plan": [
                "收集相关信息",
                "分析关键证据",
                "生成诊断报告",
            ]
        }
