import sys
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# Adiciona o diretório raiz do projeto ao sys.path para resolver imports 'from src...'
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.database import init_db
from src.rag.router import router as rag_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("microservice-ai")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando Microserviço de Inteligência (Python/FastAPI)...")
    init_db()
    yield
    logger.info("Encerrando Microserviço de Inteligência.")

app = FastAPI(
    title="Agente de troca de produtos",
    description="Serviço de Inteligência Comercial e RAG",
    version="1.0.0",
    lifespan=lifespan
)

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if "*" in origins or os.getenv("ENV", "development") == "development":
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


app.include_router(rag_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "microservice-ai",
        "embedding_model": settings.EMBEDDING_MODEL
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
