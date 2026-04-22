from app.services.intent_service import (
    INTENT_AIOPS,
    INTENT_KNOWLEDGE_QA,
    INTENT_SIMPLE_QA,
    INTENT_UNSUPPORTED,
    intent_service,
)


def test_aiops_intent_rule():
    result = intent_service.classify("帮我诊断 CPU 告警为什么一直在触发")
    assert result.intent == INTENT_AIOPS


def test_knowledge_intent_rule():
    result = intent_service.classify("根据运维文档解释一下 Prometheus 告警规则")
    assert result.intent == INTENT_KNOWLEDGE_QA


def test_cpu_concept_question_should_not_be_routed_to_aiops():
    result = intent_service.classify("请用三点概括什么是 CPU 高负载")
    assert result.intent in {INTENT_KNOWLEDGE_QA, INTENT_SIMPLE_QA}


def test_slow_response_explanation_should_prefer_knowledge_qa():
    result = intent_service.classify("结合文档解释慢响应告警一般如何定位")
    assert result.intent == INTENT_KNOWLEDGE_QA


def test_unsupported_intent_rule():
    result = intent_service.classify("帮我写一封情书")
    assert result.intent == INTENT_UNSUPPORTED
