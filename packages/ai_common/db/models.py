from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Product(Base):
    """Modelo relacional do catálogo de produtos (Worker Recommendation)."""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)

class SupportTicket(Base):
    """Modelo relacional de tickets e suporte técnico (Worker Assistant)."""
    __tablename__ = "support_tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(50), unique=True, index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False) # 'garantia', 'troca', 'defeito', 'duvida_tecnica'
    title = Column(String(255), nullable=False)
    issue_description = Column(Text, nullable=False)
    solution_guide = Column(Text, nullable=False)
    status = Column(String(50), default="RESOLVED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TaskResult(Base):
    """Modelo global para histórico e status de tarefas processadas por qualquer worker."""
    __tablename__ = "task_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    query = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
