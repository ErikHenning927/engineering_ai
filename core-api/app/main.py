import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router
from app.core.config import KAFKA_BROKER
from ai_common.kafka.async_producer import init_kafka_producer, stop_kafka_producer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("core-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando Core API Gateway e conectando recursos assíncronos...")
    try:
        await init_kafka_producer(KAFKA_BROKER)
    except Exception as e:
        logger.warning(f"⚠️ Kafka ainda não disponível no startup (será reconectado sob demanda): {e}")
    yield
    logger.info("🛑 Encerrando Core API Gateway...")
    await stop_kafka_producer()

app = FastAPI(
    title="AI API Gateway / Orquestrador Inteligente",
    description="Gateway de orquestração assíncrona com LangGraph, Guardrails defensivos e Event-Driven com Kafka.",
    version="2.0.0",
    lifespan=lifespan
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=False)
