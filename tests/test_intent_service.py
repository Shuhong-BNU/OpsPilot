from app.services.intent_service import (
    INTENT_AIOPS,
    INTENT_KNOWLEDGE_QA,
    INTENT_UNSUPPORTED,
    intent_service,
)


def test_aiops_intent_rule():
    result = intent_service.classify("帮我诊断 CPU 告警为什么一直在触发")
    assert result.intent == INTENT_AIOPS


def test_knowledge_intent_rule():
    result = intent_service.classify("根据运维文档解释一下 Prometheus 告警规则")
    assert result.intent == INTENT_KNOWLEDGE_QA


def test_unsupported_intent_rule():
    result = intent_service.classify("帮我写一封情书")
    assert result.intent == INTENT_UNSUPPORTED
