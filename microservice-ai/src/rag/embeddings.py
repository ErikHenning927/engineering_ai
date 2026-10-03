import logging
from typing import List
from openai import OpenAI
from src.config import settings

logger = logging.getLogger("microservice-ai.embeddings")

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def get_embedding(text: str) -> tuple[List[float], dict]:
    """Gera o vetor de embedding para um texto usando a API da OpenAI."""
    try:
        cleaned_text = text.replace("\n", " ")
        response = client.embeddings.create(
            input=[cleaned_text],
            model=settings.EMBEDDING_MODEL
        )
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": 0,
            "total_tokens": response.usage.total_tokens,
            "estimated_cost_usd": round(response.usage.total_tokens * 0.02 / 1_000_000, 8)
        }
        return response.data[0].embedding, usage
    except Exception as e:
        logger.error(f"Erro ao gerar embedding na OpenAI: {e}")
        raise e

def get_embeddings_batch(texts: List[str]) -> tuple[List[List[float]], dict]:
    """Gera vetores de embedding para uma lista de textos em uma única requisição (batch)."""
    try:
        cleaned_texts = [t.replace("\n", " ") for t in texts]
        response = client.embeddings.create(
            input=cleaned_texts,
            model=settings.EMBEDDING_MODEL
        )
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": 0,
            "total_tokens": response.usage.total_tokens,
            "estimated_cost_usd": round(response.usage.total_tokens * 0.02 / 1_000_000, 8)
        }
        return [item.embedding for item in response.data], usage
    except Exception as e:
        logger.error(f"Erro ao gerar batch de embeddings na OpenAI: {e}")
        raise e

