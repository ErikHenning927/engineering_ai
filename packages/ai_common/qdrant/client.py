import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

logger = logging.getLogger("ai_common.qdrant")

class QdrantManager:
    """Gerenciador centralizado de coleções e buscas no Qdrant."""
    
    def __init__(self, url: str):
        self.url = url
        self.client = QdrantClient(url=url)

    def ensure_collection(self, collection_name: str, vector_size: int = 1536, distance: qmodels.Distance = qmodels.Distance.COSINE):
        collections = self.client.get_collections().collections
        existing_names = [col.name for col in collections]
        if collection_name not in existing_names:
            logger.info(f"📦 Criando coleção '{collection_name}' no Qdrant ({vector_size} dims, {distance})...")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(size=vector_size, distance=distance)
            )

    def search_similar(self, collection_name: str, vector: list, limit: int = 3) -> List[Dict[str, Any]]:
        try:
            search_result = self.client.query_points(
                collection_name=collection_name,
                query=vector,
                limit=limit
            )
            return [hit.payload for hit in search_result.points]
        except Exception as e:
            logger.error(f"❌ Erro na busca vetorial da coleção '{collection_name}': {e}")
            return []

_default_manager: Optional[QdrantManager] = None

def get_qdrant_manager(url: str = "http://localhost:6333") -> QdrantManager:
    global _default_manager
    if _default_manager is None or _default_manager.url != url:
        _default_manager = QdrantManager(url)
    return _default_manager

def get_qdrant_client(url: str = "http://localhost:6333") -> QdrantClient:
    return get_qdrant_manager(url).client

def search_similar_vectors(url: str, collection_name: str, vector: list, limit: int = 3) -> List[Dict[str, Any]]:
    manager = get_qdrant_manager(url)
    return manager.search_similar(collection_name, vector, limit)
