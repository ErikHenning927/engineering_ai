import logging
from typing import Dict, Any, Optional, Tuple, List
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger("ai_common.qdrant.routes")

ROUTES_COLLECTION = "routes_index"

# Protótipos representativos de intenções para o roteador semântico vetorial
ROUTE_PROTOTYPES: List[Dict[str, Any]] = [
    # 🛒 Rota: Recomendação / Vendas / Catálogo (Worker Recommendation)
    {"intent": "recommend", "text": "Quero comprar um notebook ou computador de alta performance"},
    {"intent": "recommend", "text": "Pesquisar cadeira ergonômica com apoio lombar e preços"},
    {"intent": "recommend", "text": "Recomende produtos de tecnologia, monitores e periféricos do catálogo"},
    {"intent": "recommend", "text": "Qual o preço de monitor 4k ultrawide ou teclado mecânico sem fio?"},
    {"intent": "recommend", "text": "Gostaria de ver produtos à venda, valores e promoções"},
    {"intent": "recommend", "text": "Procurando mesa elétrica com regulagem de altura e mouse ergonômico"},
    {"intent": "recommend", "text": "Catálogo de vendas, buscar itens novos e especificações técnicas de compra"},
    {"intent": "recommend", "text": "Quais modelos de headset e teclado vocês vendem?"},
    {"intent": "recommend", "text": "Notebook Pro X, Cadeira Max Confort, Monitor Ultrawide"},
    {"intent": "recommend", "text": "Quero comprar periféricos gamer e para escritório"},

    # 🛠️ Rota: Suporte Técnico / Garantia / Trocas / Avarias (Worker Assistant)
    {"intent": "support", "text": "Meu produto veio com defeito, quebrado ou avariado"},
    {"intent": "support", "text": "Como acionar a garantia ou solicitar assistência técnica?"},
    {"intent": "support", "text": "Ajuste de altura travado ou erro E01 E02 no painel da mesa"},
    {"intent": "support", "text": "Apoio de braço quebrado ou folga no pistão da cadeira ergonômica"},
    {"intent": "support", "text": "Monitor com dead pixel, linhas na tela ou falha no display"},
    {"intent": "support", "text": "Como parear o teclado mecânico wireless bluetooth no computador"},
    {"intent": "support", "text": "Headset com ruído estático no cancelamento de ruído ANC ou microfone mudo"},
    {"intent": "support", "text": "Política de troca expressa, logística reversa e RMA"},
    {"intent": "support", "text": "Preciso de ajuda técnica com meu aparelho que parou de funcionar"},
    {"intent": "support", "text": "Dúvida sobre conserto, peças de reposição e manuais de solução"},

    # 💬 Rota: Conversa Fiada / Saudações (Direct Fallback)
    {"intent": "small_talk", "text": "Olá, bom dia! Tudo bem com você?"},
    {"intent": "small_talk", "text": "Oi, boa tarde, como vai?"},
    {"intent": "small_talk", "text": "Quem é você e o que você faz?"},
    {"intent": "small_talk", "text": "Obrigado pela ajuda, até logo!"},
    {"intent": "small_talk", "text": "Boa noite! Pode me ajudar?"},
    {"intent": "small_talk", "text": "Tchau, valeu!"}
]

def ensure_routes_collection(q_client: QdrantClient):
    """Garante que a coleção de rotas exista no Qdrant."""
    collections = [c.name for c in q_client.get_collections().collections]
    if ROUTES_COLLECTION not in collections:
        logger.info(f"📦 Criando coleção de rotas '{ROUTES_COLLECTION}' no Qdrant...")
        q_client.create_collection(
            collection_name=ROUTES_COLLECTION,
            vectors_config=qmodels.VectorParams(size=1536, distance=qmodels.Distance.COSINE),
        )

def seed_routes(qdrant_url: str, openai_api_key: str):
    """Popula os vetores das rotas no Qdrant."""
    q_client = QdrantClient(url=qdrant_url)
    ensure_routes_collection(q_client)
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)

    points = []
    for idx, item in enumerate(ROUTE_PROTOTYPES, start=1):
        vec = embeddings.embed_query(item["text"])
        points.append(
            qmodels.PointStruct(
                id=idx,
                vector=vec,
                payload={
                    "route_id": idx,
                    "intent": item["intent"],
                    "sample_text": item["text"]
                }
            )
        )

    q_client.upsert(collection_name=ROUTES_COLLECTION, points=points)
    logger.info(f"✅ {len(points)} protótipos de rotas indexados na coleção '{ROUTES_COLLECTION}'!")

class VectorRouter:
    """Roteador Semântico Vetorial Ultra-Rápido (< 50ms) usando Qdrant."""
    
    def __init__(self, qdrant_url: str, openai_api_key: str):
        self.q_client = QdrantClient(url=qdrant_url)
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        ensure_routes_collection(self.q_client)

    async def aclassify_query(self, query: str, min_confidence: float = 0.50) -> Tuple[str, float, str]:
        """Classifica a intenção de uma query através de similaridade de cosseno vetorial."""
        try:
            vector = await self.embeddings.aembed_query(query)
            result = self.q_client.query_points(
                collection_name=ROUTES_COLLECTION,
                query=vector,
                limit=1
            )
            if result.points:
                top_hit = result.points[0]
                score = top_hit.score
                intent = top_hit.payload.get("intent", "unclear")
                sample = top_hit.payload.get("sample_text", "")
                
                if score >= min_confidence:
                    return intent, score, sample
                else:
                    return "unclear", score, sample
            return "unclear", 0.0, ""
        except Exception as e:
            logger.error(f"❌ Erro no roteamento vetorial: {e}")
            return "unclear", 0.0, str(e)
