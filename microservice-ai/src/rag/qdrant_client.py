import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from src.config import settings

logger = logging.getLogger("microservice-ai.qdrant")

_client = None

def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        logger.info(f"Inicializando cliente Qdrant na URL: {settings.QDRANT_URL}")
        _client = QdrantClient(url=settings.QDRANT_URL)
    return _client

def init_products_collection(vector_size: int = 1536):
    client = get_qdrant_client()
    collection_name = settings.QDRANT_COLLECTION
    
    try:
        if not client.collection_exists(collection_name):
            logger.info(f"Criando coleção do Qdrant: {collection_name}")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Coleção {collection_name} criada com sucesso.")
        else:
            logger.info(f"Coleção {collection_name} já existe no Qdrant.")
    except Exception as e:
        logger.error(f"Erro ao inicializar coleção {collection_name} no Qdrant: {e}")
        raise e
