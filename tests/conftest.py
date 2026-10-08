import os
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 1. Configurações de ambiente para testes
os.environ.setdefault("LITELLM_URL", "http://litellm:4000")
os.environ.setdefault("QDRANT_URL", "http://qdrant:6333")
os.environ.setdefault("KAFKA_BROKER", "kafka:9092")
os.environ["POSTGRES_URL"] = "sqlite:///:memory:"

from ai_common.db.models import Base

# 2. Fixture do Banco de Dados em Memória (SQLite com StaticPool)
@pytest.fixture
def db_session():
    """Cria uma sessão isolada de banco de dados em memória para testes."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()

# 3. Fixture do TestClient da API FastAPI
@pytest.fixture
def client(monkeypatch, db_session):
    """Retorna um TestClient para a Core API com Kafka e DB mockados."""
    mock_publish = AsyncMock(return_value=True)
    monkeypatch.setattr("ai_common.kafka.async_producer.publish_task", mock_publish)
    monkeypatch.setattr("app.agent.orchestrator.publish_task", mock_publish)
    
    from app.main import app
    from ai_common.db.session import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
        
    app.dependency_overrides.clear()

# 4. Dados de Teste Comuns
@pytest.fixture
def sample_product_data():
    return {
        "name": "Notebook Pro X",
        "description": "Notebook Intel Core i9 com 32GB RAM e RTX 4070",
        "price": 14999.00
    }

@pytest.fixture
def sample_ticket_data():
    return {
        "ticket_number": "TCK-999",
        "category": "troca",
        "title": "Monitor com Dead Pixel",
        "issue_description": "Tela com dead pixel no primeiro dia de uso.",
        "solution_guide": "Política de troca expressa em 7 dias.",
        "status": "RESOLVED"
    }
