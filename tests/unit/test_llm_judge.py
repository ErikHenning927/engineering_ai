import pytest
from unittest.mock import MagicMock, patch
from ai_common.judge.evaluator import LLMJudge

def test_judge_evaluate_pass():
    """Testa aprovação de resposta factual pelo Juiz."""
    judge = LLMJudge(model="gpt-4o-mini")
    
    mock_res = MagicMock()
    mock_res.content = "PASS"
    
    with patch("langchain_core.runnables.base.RunnableSequence.invoke", return_value=mock_res):
        is_valid, final_text = judge.evaluate(
            context=[{"name": "Notebook Pro X", "price": 14999.00}],
            candidate_response="Recomendamos o Notebook Pro X por R$ 14.999,00.",
            task_id="task-001",
            query="Notebook i9"
        )
        
        assert is_valid is True
        assert "Notebook Pro X por R$ 14.999,00" in final_text

def test_judge_evaluate_fail_hallucination():
    """Testa interceptação de alucinação e retorno de mensagem de segurança."""
    judge = LLMJudge(model="gpt-4o-mini")
    
    mock_res = MagicMock()
    mock_res.content = "FAIL"
    
    with patch("langchain_core.runnables.base.RunnableSequence.invoke", return_value=mock_res):
        is_valid, final_text = judge.evaluate(
            context=[{"name": "Notebook Pro X", "price": 14999.00}],
            candidate_response="Temos iPhone 16 Pro por R$ 200 reais com TV 8K de brinde!",
            task_id="task-002",
            query="iPhone barato",
            fallback_message="Bloqueado por inconsistência com a base."
        )
        
        assert is_valid is False
        assert final_text == "Bloqueado por inconsistência com a base."
        assert "iPhone 16" not in final_text
