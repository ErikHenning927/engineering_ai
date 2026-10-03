from qdrant_client import QdrantClient
from app.core.config import QDRANT_URL

client = QdrantClient(url=QDRANT_URL)

def search_similar_products(vector: list, limit: int = 2):
    search_result = client.query_points(
        collection_name="products",
        query=vector,
        limit=limit
    )
    return [hit.payload for hit in search_result.points]
