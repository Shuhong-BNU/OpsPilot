"""规则优先的意图识别服务。"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_qwq import ChatQwen
from loguru import logger

from app.config import config


INTENT_SMALLTALK = "smalltalk"
INTENT_SIMPLE_QA = "simple_qa"
INTENT_KNOWLEDGE_QA = "knowledge_qa"
INTENT_AIOPS = "aiops_diagnosis"
INTENT_UNSUPPORTED = "unsupported"


@dataclass
class IntentResult:
    intent: str
    reason: str
    confidence: float


class IntentService:
    """规则优先，不确定时回退到轻量 LLM 分类。"""

    SMALLTALK_KEYWORDS = ("你好", "您好", "hi", "hello", "谢谢", "你是谁", "早上好", "晚上好")
    AIOPS_CORE_KEYWORDS = (
        "告警",
        "报警",
        "排障",
        "诊断",
        "故障",
        "根因",
        "修复",
        "恢复",
        "异常",
    )
    AIOPS_SIGNAL_KEYWORDS = (
        "cpu",
        "内存",
        "磁盘",
        "连接池",
        "超时",
        "服务不可用",
        "慢响应",
        "错误率",
        "负载",
        "熔断",
        "root cause",
        "alert",
        "latency",
    )
    DIAGNOSIS_ACTION_KEYWORDS = ("分析", "定位", "排查", "处理", "排障", "诊断", "修复", "恢复")
    KNOWLEDGE_CONTEXT_KEYWORDS = (
        "根据知识库",
        "根据文档",
        "结合知识库",
        "结合文档",
        "文档中",
        "知识库里",
        "runbook 中",
        "解释",
        "概括",
        "介绍",
        "说明",
        "总结",
        "常见排查步骤",
        "如何定位",
    )
    LIVE_DIAGNOSIS_KEYWORDS = (
        "当前系统",
        "当前服务",
        "当前环境",
        "现在",
        "当前是否",
        "是否存在告警",
        "帮我诊断",
        "诊断当前",
        "在线诊断",
        "立即诊断",
        "告警为什么一直在触发",
        "看一下告警",
    )
    KNOWLEDGE_KEYWORDS = (
        "知识库",
        "文档",
        "runbook",
        "手册",
        "prometheus",
        "kubernetes",
        "linux",
        "运维",
        "mcp",
        "rag",
        "监控",
        "怎么配置",
        "原理",
        "什么是",
        "解释",
        "概括",
        "介绍",
        "含义",
    )
    KNOWLEDGE_SIGNAL_KEYWORDS = (
        "cpu",
        "内存",
        "磁盘",
        "连接池",
        "服务不可用",
        "慢响应",
        "告警规则",
        "prometheus",
        "kubernetes",
        "linux",
    )
    UNSUPPORTED_KEYWORDS = ("写情书", "情书", "算命", "股票推荐", "彩票", "生成图片", "娱乐八卦")

    def __init__(self) -> None:
        self._classifier = None

    def classify(self, query: str) -> IntentResult:
        """返回意图分类结果。"""
        text = query.strip()
        lowered = text.lower()

        if not text:
            return IntentResult(INTENT_SMALLTALK, "空消息按闲聊处理", 1.0)

        if any(keyword in text for keyword in self.UNSUPPORTED_KEYWORDS):
            return IntentResult(INTENT_UNSUPPORTED, "命中越界/无关规则", 0.98)

        if any(keyword in lowered for keyword in self.SMALLTALK_KEYWORDS):
            return IntentResult(INTENT_SMALLTALK, "命中寒暄规则", 0.95)

        has_aiops_core = any(keyword in lowered for keyword in self.AIOPS_CORE_KEYWORDS)
        has_aiops_signal = any(keyword in lowered for keyword in self.AIOPS_SIGNAL_KEYWORDS)
        has_diagnosis_action = any(keyword in lowered for keyword in self.DIAGNOSIS_ACTION_KEYWORDS)
        has_knowledge_context = any(keyword in lowered for keyword in self.KNOWLEDGE_CONTEXT_KEYWORDS)
        has_knowledge_signal = any(keyword in lowered for keyword in self.KNOWLEDGE_SIGNAL_KEYWORDS)
        has_knowledge_keyword = any(keyword in lowered for keyword in self.KNOWLEDGE_KEYWORDS)
        has_live_diagnosis = any(keyword in lowered for keyword in self.LIVE_DIAGNOSIS_KEYWORDS)

        # 解释型、文档型问题优先走 knowledge_qa，避免“告警 + 定位”被误判成 AIOps。
        if (has_knowledge_context or has_knowledge_keyword) and not has_live_diagnosis:
            return IntentResult(INTENT_KNOWLEDGE_QA, "命中文档/知识解释规则", 0.92)

        if has_aiops_core and has_live_diagnosis:
            return IntentResult(INTENT_AIOPS, "命中在线诊断规则", 0.95)

        if has_aiops_core and has_diagnosis_action and not (has_knowledge_context or has_knowledge_keyword):
            return IntentResult(INTENT_AIOPS, "命中故障诊断规则", 0.93)

        if has_aiops_signal and has_diagnosis_action and has_live_diagnosis:
            return IntentResult(INTENT_AIOPS, "命中信号诊断规则", 0.9)

        if has_knowledge_signal and (has_knowledge_context or has_knowledge_keyword or has_diagnosis_action):
            return IntentResult(INTENT_KNOWLEDGE_QA, "命中运维知识问答规则", 0.88)

        if has_knowledge_signal and any(keyword in lowered for keyword in ("什么是", "解释", "概括", "介绍", "原理")):
            return IntentResult(INTENT_KNOWLEDGE_QA, "命中运维概念解释规则", 0.88)

        if len(text) <= 18:
            return IntentResult(INTENT_SIMPLE_QA, "短问题默认走轻问答链路", 0.8)

        llm_result = self._classify_with_llm(text)
        if llm_result:
            return llm_result

        return IntentResult(INTENT_SIMPLE_QA, "未命中规则且 LLM 不可用，回退到简单问答", 0.6)

    def _classify_with_llm(self, query: str) -> IntentResult | None:
        """使用轻量 LLM 做兜底分类。"""
        if not config.dashscope_api_key:
            return None

        if self._classifier is None:
            self._classifier = ChatQwen(
                model=config.rag_model,
                api_key=config.dashscope_api_key,
                temperature=0,
                streaming=False,
            )

        prompt = f"""
你是 OpsPilot 的意图分类器。只能输出一个标签：
smalltalk, simple_qa, knowledge_qa, aiops_diagnosis, unsupported

分类规则：
- smalltalk：寒暄、感谢、自我介绍
- simple_qa：简单事实问答，不依赖知识库或诊断
- knowledge_qa：需要运维文档、知识库、RAG 支撑
- aiops_diagnosis：告警、故障分析、排障、根因定位
- unsupported：明显越界或与智能运维助手无关

用户问题：{query}
""".strip()

        try:
            result = self._classifier.invoke(prompt)
            label = (result.content if hasattr(result, "content") else str(result)).strip().lower()
            if label in {
                INTENT_SMALLTALK,
                INTENT_SIMPLE_QA,
                INTENT_KNOWLEDGE_QA,
                INTENT_AIOPS,
                INTENT_UNSUPPORTED,
            }:
                return IntentResult(label, "LLM 兜底分类", 0.7)
        except Exception as exc:
            logger.warning(f"LLM 意图分类失败，回退规则: {exc}")
        return None


intent_service = IntentService()
