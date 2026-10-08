import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../../.env"))

logger = logging.getLogger("ai_common.db")

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+psycopg2://ai_user:ai_password@127.0.0.1:5432/ai_db")

engine = create_engine(
    POSTGRES_URL, 
    pool_pre_ping=True, 
    pool_size=10, 
    max_overflow=20
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI Dependency para injeção de sessão de banco."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_session():
    """Context manager para uso de banco em scripts e workers."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def save_task_result(task_id: str, query: str, response: str):
    """Função utilitária unificada para gravar a resposta de qualquer worker."""
    from .models import TaskResult
    with get_db_session() as session:
        new_result = TaskResult(
            task_id=task_id,
            query=query,
            agent_response=response
        )
        session.add(new_result)
        logger.info(f"💾 [DB] Resultado da tarefa '{task_id}' persistido com sucesso no PostgreSQL.")
