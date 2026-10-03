from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class TaskResult(Base):
    __tablename__ = "task_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    query = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
