import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from langchain_openai import OpenAIEmbeddings

# Adiciona a pasta raiz ao sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

from app.db.models import Base, Product

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+psycopg2://ai_user:ai_password@postgres:5432/ai_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

COLLECTION_NAME = "products"

SAMPLE_PRODUCTS = [
    {
        "name": "Notebook Pro X",
        "description": "Notebook de alta performance com processador Intel Core i9, 32GB RAM, SSD 1TB NVMe e GPU dedicada RTX 4070 para desenvolvimento de IA, modelagem 3D e multitarefas pesadas.",
        "price": 14999.00
    },
    {
        "name": "Cadeira Ergonômica Max Confort",
        "description": "Cadeira ergonômica premium com suporte lombar dinâmico ajustável, apoio de braço 3D, encosto em tela mesh respirável e ajuste de inclinação para longas jornadas de trabalho.",
        "price": 1299.90
    },
    {
        "name": "Monitor Ultrawide 34\" 4K",
        "description": "Monitor curvo ultrawide de 34 polegadas com resolução 4K, taxa de atualização de 144Hz, painel IPS HDR400, ideal para programação, leitura de múltiplos documentos e produtividade.",
        "price": 3499.00
    },
    {
        "name": "Teclado Mecânico Wireless Pro",
        "description": "Teclado mecânico sem fio compacto (75%) com switches silenciosos Red, iluminação RGB personalizável, layout ABNT2 e conexão Bluetooth / 2.4GHz com bateria para 200 horas.",
        "price": 549.90
    },
    {
        "name": "Mouse Ergonômico Vertical",
        "description": "Mouse sem fio ergonômico vertical projetado para reduzir a tensão muscular e prevenir LER/DORT, com sensor óptico ajustável até 4000 DPI e cliques silenciosos.",
        "price": 289.00
    },
    {
        "name": "Mesa Elétrica com Regulagem de Altura",
        "description": "Mesa inteligente com motor duplo silencioso, ajuste de altura motorizado com painel touch e 4 memórias programáveis para alternar entre trabalhar em pé ou sentado.",
        "price": 2799.00
    },
    {
        "name": "Headset Noise Cancelling Pro",
        "description": "Headset wireless premium com cancelamento ativo de ruído (ANC híbrido), microfone direcional com isolamento de voz por IA e autonomia de até 40 horas.",
        "price": 989.00
    }
]

def seed():
    print("==================================================")
    print("🌱 Iniciando Processo de Seed de Produtos")
    print(f"🔗 Postgres URL: {POSTGRES_URL}")
    print(f"🔗 Qdrant URL: {QDRANT_URL}")
    print("==================================================")

    # 1. Configurar Banco Relacional
    engine = create_engine(POSTGRES_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 2. Configurar Banco Vetorial (Qdrant)
    q_client = QdrantClient(url=QDRANT_URL)
    
    # Criar ou verificar coleção no Qdrant
    collections = q_client.get_collections().collections
    collection_names = [col.name for col in collections]
    
    if COLLECTION_NAME not in collection_names:
        print(f"📦 Criando coleção '{COLLECTION_NAME}' no Qdrant (1536 dimensões, Cosine)...")
        q_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(size=1536, distance=qmodels.Distance.COSINE),
        )
    else:
        print(f"📦 Coleção '{COLLECTION_NAME}' já existe no Qdrant.")

    # 3. Inicializar embeddings
    if not OPENAI_API_KEY:
        print("❌ ERRO: OPENAI_API_KEY não foi encontrada no ambiente!")
        sys.exit(1)

    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    # 4. Inserir produtos e gerar vetores
    total_inserted = 0
    for item in SAMPLE_PRODUCTS:
        existing = session.query(Product).filter(Product.name == item["name"]).first()
        if existing:
            product_id = existing.id
            print(f"ℹ️ Produto '{item['name']}' já existe no Postgres (ID: {product_id}). Atualizando dados...")
            existing.description = item["description"]
            existing.price = item["price"]
            session.commit()
        else:
            new_prod = Product(
                name=item["name"],
                description=item["description"],
                price=item["price"]
            )
            session.add(new_prod)
            session.commit()
            session.refresh(new_prod)
            product_id = new_prod.id
            print(f"➕ Inserido no Postgres: '{item['name']}' (ID: {product_id})")

        # Gerar embedding do texto (nome + descrição para melhor relevância semântica)
        text_to_embed = f"{item['name']}: {item['description']}"
        vector = embeddings.embed_query(text_to_embed)

        # Upsert no Qdrant
        q_client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                qmodels.PointStruct(
                    id=product_id,
                    vector=vector,
                    payload={
                        "id": product_id,
                        "name": item["name"],
                        "description": item["description"],
                        "price": item["price"]
                    }
                )
            ]
        )
        print(f"🎯 Vetorizado e indexado no Qdrant: ID {product_id}")
        total_inserted += 1

    session.close()
    print("\n✅ Seed concluído com sucesso!")
    print(f"📊 Total de produtos sincronizados: {total_inserted}")
    print("==================================================")

if __name__ == "__main__":
    seed()
