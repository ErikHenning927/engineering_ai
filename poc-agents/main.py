import os
import uuid
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate
import PyPDF2
import io
from dotenv import load_dotenv

# Carrega o .env da raiz do projeto
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# --- Configurações ---
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+psycopg2://ai_user:ai_password@localhost:5432/ai_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-mock-key") # Substitua pela sua chave real depois

# --- Banco de Dados Relacional (Postgres) ---
engine = create_engine(POSTGRES_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    price = Column(Float)

# Cria as tabelas na inicialização (No futuro, o Alembic fará isso)
Base.metadata.create_all(bind=engine)

# --- Banco Vetorial (Qdrant) ---
q_client = QdrantClient(url=QDRANT_URL)
COLLECTION_NAME = "products"

try:
    q_client.get_collection(COLLECTION_NAME)
except:
    q_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=qmodels.VectorParams(size=1536, distance=qmodels.Distance.COSINE),
    )

# --- Modelos de IA ---
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
llm = ChatOpenAI(temperature=0.2, openai_api_key=OPENAI_API_KEY)

app = FastAPI(title="Orquestrador AI - PoC")

# ==========================================
# 1. Endpoint de SEED (Postgres + Qdrant)
# ==========================================
@app.post("/seed")
def seed_database():
    db = SessionLocal()
    
    # Verifica se já tem dados para não duplicar
    if db.query(Product).first():
        db.close()
        return {"message": "Banco já está populado."}

    sample_products = [
        {"name": "Notebook Pro X", "description": "Notebook de alta performance com 32GB RAM e GPU dedicada para IA.", "price": 15000.0},
        {"name": "Cadeira Ergonômica Max", "description": "Cadeira confortável para desenvolvedores com suporte lombar ajustável.", "price": 1200.0},
        {"name": "Monitor Ultrawide 34", "description": "Monitor curvo ultrawide 4k perfeito para produtividade e ler código.", "price": 3500.0},
    ]
    
    for p in sample_products:
        # Salva no Postgres
        db_prod = Product(name=p["name"], description=p["description"], price=p["price"])
        db.add(db_prod)
        db.commit()
        db.refresh(db_prod)
        
        # Vetoriza a descrição e salva no Qdrant
        vector = embeddings.embed_query(p["description"])
        q_client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                qmodels.PointStruct(
                    id=db_prod.id,
                    vector=vector,
                    payload={"name": p["name"], "price": p["price"], "description": p["description"]}
                )
            ]
        )
    db.close()
    return {"message": "Seed concluído! Produtos inseridos no Postgres e vetorizados no Qdrant."}

# ==========================================
# 2. Agente de Leitura de PDF
# ==========================================
def process_pdf(file_bytes: bytes) -> str:
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in pdf_reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

# ==========================================
# 3. Agente de Recomendação de Produtos
# ==========================================
def recommend_products(query: str):
    # 3.1. Vetoriza a busca do usuário
    vector = embeddings.embed_query(query)
    
    # 3.2. Busca por similaridade no Qdrant
    search_result = q_client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=2
    )
    
    recommendations = [hit.payload for hit in search_result.points]
    
    if not recommendations:
         return {"recommendations": [], "llm_answer": "Não encontrei produtos similares."}
    
    # 3.3. Passa o contexto para o LLM formular uma resposta humana
    prompt = PromptTemplate.from_template(
        "Você é um assistente de vendas amigável. Baseado SOMENTE nos seguintes produtos do nosso banco: {produtos}, responda à necessidade do cliente: '{query}'. Tente sugerir qual o melhor encaixe."
    )
    chain = prompt | llm
    response = chain.invoke({"produtos": recommendations, "query": query})
    
    return {"recommendations": recommendations, "llm_answer": response.content}

# ==========================================
# 4. Orquestrador (O "Cérebro" Gateway)
# ==========================================
@app.post("/orchestrate")
async def orchestrate(
    intent: str = Form(..., description="'read_pdf' ou 'recommend'"),
    query: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    Este endpoint simula o cérebro. Ele recebe a intenção e roteia para o agente correto.
    """
    if intent == "read_pdf" and file:
        content = await file.read()
        extracted_text = process_pdf(content)
        return {
            "agent": "PDF Reader", 
            "status": "success", 
            "extracted_text": extracted_text[:300] + "... [texto truncado para resposta]"
        }
    
    elif intent == "recommend" and query:
        result = recommend_products(query)
        return {
            "agent": "Product Recommender", 
            "status": "success", 
            "result": result
        }
        
    return {"status": "error", "message": "Parâmetros inválidos. Verifique a intenção (intent)."}

if __name__ == "__main__":
    import uvicorn
    # Roda o servidor na porta 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
