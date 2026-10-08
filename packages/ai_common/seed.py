import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from langchain_openai import OpenAIEmbeddings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

from ai_common.db.models import Base, Product, SupportTicket

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+psycopg2://ai_user:ai_password@postgres:5432/ai_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PRODUCTS_COLLECTION = "products"
SUPPORT_COLLECTION = "support_knowledge"

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

SAMPLE_TICKETS = [
    {
        "ticket_number": "TCK-101",
        "category": "defeito",
        "title": "Ajuste de Altura Travado na Mesa Elétrica",
        "issue_description": "Mesa elétrica com motor duplo parou de subir/descer ou apresenta código de erro E01/E02 no painel touch.",
        "solution_guide": "1. Pressione o botão DOWN por 10 segundos até ouvir um bipe para resetar a calibração do motor duplo. 2. Verifique se todos os cabos de alimentação da caixa de controle estão firmes. 3. Caso o problema persista, acione a troca do painel de controle ou motor sob a garantia de 5 anos.",
        "status": "RESOLVED"
    },
    {
        "ticket_number": "TCK-102",
        "category": "garantia",
        "title": "Apoio de Braço Quebrado ou Folga na Cadeira Ergonômica",
        "issue_description": "O apoio de braço 3D da Cadeira Ergonômica Max Confort soltou ou o mecanismo de inclinação perdeu a pressão.",
        "solution_guide": "A garantia de 3 anos cobre a substituição imediata de peças estruturais (braços 3D, pistão a gás classe 4 e rodízios PU). Não é necessário enviar a cadeira inteira; enviamos a peça de reposição em até 3 dias úteis.",
        "status": "RESOLVED"
    },
    {
        "ticket_number": "TCK-103",
        "category": "troca",
        "title": "Monitor com Dead Pixel ou Linhas Verticais na Tela",
        "issue_description": "Monitor Ultrawide 34 4K recebido com dead pixel ou falha de sinal no painel IPS.",
        "solution_guide": "Política de Troca Expressa: Dentro dos primeiros 7 dias após o recebimento, geramos o código de logística reversa e despachamos um novo monitor lacrado imediatamente após a postagem nos Correios.",
        "status": "RESOLVED"
    },
    {
        "ticket_number": "TCK-104",
        "category": "duvida_tecnica",
        "title": "Como Parear Teclado Mecânico Wireless via Bluetooth",
        "issue_description": "Dúvida sobre conexão do Teclado Mecânico Wireless Pro com Mac/Windows e alternância de dispositivos.",
        "solution_guide": "Pressione Fn + Q (Dispositivo 1), Fn + W (Dispositivo 2) ou Fn + E (Dispositivo 3) por 5 segundos para entrar em modo pareamento. Para o modo 2.4GHz com dongle USB, pressione Fn + R.",
        "status": "RESOLVED"
    },
    {
        "ticket_number": "TCK-105",
        "category": "defeito",
        "title": "Ruído Estático no Cancelamento de Ruído do Headset",
        "issue_description": "Headset Noise Cancelling Pro com ruído estático ou microfone mudo no modo sem fio.",
        "solution_guide": "1. Atualize o firmware pelo aplicativo oficial. 2. Realize o hard reset segurando Power + Mute por 15 segundos. Se o ruído no ANC persistir, acione a substituição do produto via RMA.",
        "status": "RESOLVED"
    }
]

def seed_all():
    print("==================================================")
    print("🌱 Iniciando Seed da Plataforma (Produtos + Suporte & Tickets)")
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
    
    # Criar coleções se não existirem
    collections = [c.name for c in q_client.get_collections().collections]
    
    for col_name in [PRODUCTS_COLLECTION, SUPPORT_COLLECTION]:
        if col_name not in collections:
            print(f"📦 Criando coleção '{col_name}' no Qdrant (1536 dimensões, Cosine)...")
            q_client.create_collection(
                collection_name=col_name,
                vectors_config=qmodels.VectorParams(size=1536, distance=qmodels.Distance.COSINE),
            )
        else:
            print(f"📦 Coleção '{col_name}' já existe no Qdrant.")

    if not OPENAI_API_KEY:
        print("❌ ERRO: OPENAI_API_KEY não encontrada no ambiente!")
        sys.exit(1)

    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    # 3. Seed de Produtos (Worker Recommendation)
    print("\n--- 🛒 Populando Catálogo de Produtos ---")
    for item in SAMPLE_PRODUCTS:
        existing = session.query(Product).filter(Product.name == item["name"]).first()
        if existing:
            product_id = existing.id
            existing.description = item["description"]
            existing.price = item["price"]
            session.commit()
        else:
            new_prod = Product(name=item["name"], description=item["description"], price=item["price"])
            session.add(new_prod)
            session.commit()
            session.refresh(new_prod)
            product_id = new_prod.id
            print(f"➕ Produto inserido no Postgres: '{item['name']}' (ID: {product_id})")

        vector = embeddings.embed_query(f"{item['name']}: {item['description']}")
        q_client.upsert(
            collection_name=PRODUCTS_COLLECTION,
            points=[
                qmodels.PointStruct(
                    id=product_id,
                    vector=vector,
                    payload={"id": product_id, "name": item["name"], "description": item["description"], "price": item["price"]}
                )
            ]
        )
        print(f"🎯 Vetorizado no Qdrant ['{PRODUCTS_COLLECTION}']: ID {product_id}")

    # 4. Seed de Tickets e Base de Suporte (Worker Assistant)
    print("\n--- 🛠️ Populando Tickets e Base de Suporte Técnico ---")
    for ticket in SAMPLE_TICKETS:
        existing_tck = session.query(SupportTicket).filter(SupportTicket.ticket_number == ticket["ticket_number"]).first()
        if existing_tck:
            ticket_id = existing_tck.id
            existing_tck.title = ticket["title"]
            existing_tck.issue_description = ticket["issue_description"]
            existing_tck.solution_guide = ticket["solution_guide"]
            existing_tck.category = ticket["category"]
            session.commit()
        else:
            new_tck = SupportTicket(
                ticket_number=ticket["ticket_number"],
                category=ticket["category"],
                title=ticket["title"],
                issue_description=ticket["issue_description"],
                solution_guide=ticket["solution_guide"],
                status=ticket["status"]
            )
            session.add(new_tck)
            session.commit()
            session.refresh(new_tck)
            ticket_id = new_tck.id
            print(f"➕ Ticket inserido no Postgres: '{ticket['ticket_number']} - {ticket['title']}' (ID: {ticket_id})")

        text_to_embed = f"Ticket {ticket['ticket_number']} - {ticket['title']} ({ticket['category']}): {ticket['issue_description']} -> Solução: {ticket['solution_guide']}"
        vector = embeddings.embed_query(text_to_embed)
        q_client.upsert(
            collection_name=SUPPORT_COLLECTION,
            points=[
                qmodels.PointStruct(
                    id=ticket_id,
                    vector=vector,
                    payload={
                        "id": ticket_id,
                        "ticket_number": ticket["ticket_number"],
                        "category": ticket["category"],
                        "title": ticket["title"],
                        "issue_description": ticket["issue_description"],
                        "solution_guide": ticket["solution_guide"]
                    }
                )
            ]
        )
        print(f"🎯 Vetorizado no Qdrant ['{SUPPORT_COLLECTION}']: Ticket {ticket['ticket_number']}")

    session.close()
    print("\n✅ Seed Completo Concluído com Sucesso!")
    print("==================================================")

if __name__ == "__main__":
    seed_all()
