import pytest
from app.agent.orchestrator import SecurityEvaluation, IntentClassification

def test_security_evaluation_model_safe():
    """Valida modelo Pydantic para entrada legítima e segura."""
    eval_safe = SecurityEvaluation(
        is_safe=True,
        reasoning="Usuário solicitou catálogo de notebooks legitimamente.",
        threat_category="none"
    )
    assert eval_safe.is_safe is True
    assert eval_safe.threat_category == "none"

def test_security_evaluation_model_threat():
    """Valida modelo Pydantic para detecção de Prompt Injection."""
    eval_threat = SecurityEvaluation(
        is_safe=False,
        reasoning="Tentativa explícita de sobrescrever regras do sistema.",
        threat_category="prompt_injection"
    )
    assert eval_threat.is_safe is False
    assert eval_threat.threat_category == "prompt_injection"

def test_intent_classification_model():
    """Valida modelo Pydantic para classificação de intenção."""
    intent_data = IntentClassification(
        reasoning="Cliente deseja suporte técnico para monitor com defeito.",
        intent="support",
        product="Monitor Ultrawide 34"
    )
    assert intent_data.intent == "support"
    assert intent_data.product == "Monitor Ultrawide 34"
