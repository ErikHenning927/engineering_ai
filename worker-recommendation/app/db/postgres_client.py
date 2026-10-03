import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import TaskResult

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+psycopg2://ai_user:ai_password@127.0.0.1:5432/ai_db")

engine = create_engine(POSTGRES_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def save_result(task_id: str, query: str, response: str):
    db = SessionLocal()
    try:
        new_result = TaskResult(
            task_id=task_id,
            query=query,
            agent_response=response
        )
        db.add(new_result)
        db.commit()
    except Exception as e:
        print(f"[DB Error] Falha ao salvar no banco: {e}")
        db.rollback()
    finally:
        db.close()
