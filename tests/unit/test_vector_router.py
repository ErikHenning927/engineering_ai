import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ai_common.qdrant.routes import VectorRouter, ROUTE_PROTOTYPES

@pytest.mark.asyncio
async def test_vector_router_classification_hit():
    """Testa classificação com score acima do threshold."""
    router = VectorRouter(qdrant_url="http://mock-qdrant:6333", openai_api_key="sk-test")
    
    mock_hit = MagicMock()
    mock_hit.score = 0.92
    mock_hit.payload = {"intent": "recommend", "sample_text": "Quero comprar um notebook"}
    
    mock_result = MagicMock()
    mock_result.points = [mock_hit]
    
    with patch("langchain_openai.OpenAIEmbeddings.aembed_query", AsyncMock(return_value=[0.1] * 1536)):
        with patch.object(router.q_client, "query_points", return_value=mock_result):
            intent, score, sample = await router.aclassify_query("Notebook novo para trabalho", min_confidence=0.50)
            
            assert intent == "recommend"
            assert score == 0.92
            assert "comprar um notebook" in sample

@pytest.mark.asyncio
async def test_vector_router_classification_low_confidence():
    """Testa retorno 'unclear' quando a similaridade for inferior ao threshold."""
    router = VectorRouter(qdrant_url="http://mock-qdrant:6333", openai_api_key="sk-test")
    
    mock_hit = MagicMock()
    mock_hit.score = 0.35  # Baixa confiança
    mock_hit.payload = {"intent": "support", "sample_text": "Ajuda com defeito"}
    
    mock_result = MagicMock()
    mock_result.points = [mock_hit]
    
    with patch("langchain_openai.OpenAIEmbeddings.aembed_query", AsyncMock(return_value=[0.1] * 1536)):
        with patch.object(router.q_client, "query_points", return_value=mock_result):
            intent, score, sample = await router.aclassify_query("Frase completamente aleatória", min_confidence=0.50)
            
            assert intent == "unclear"
            assert score == 0.35

def test_route_prototypes_structure():
    """Valida se os protótipos de rotas possuem intenções válidas e textos ricos."""
    valid_intents = {"recommend", "support", "small_talk"}
    assert len(ROUTE_PROTOTYPES) >= 10
    
    for proto in ROUTE_PROTOTYPES:
        assert proto["intent"] in valid_intents
        assert len(proto["text"]) > 5
