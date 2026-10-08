import pytest
from datetime import datetime
from ai_common.db.models import Product, SupportTicket, TaskResult

def test_create_and_query_product(db_session, sample_product_data):
    """Testa criação e consulta de produtos no banco relacional."""
    product = Product(**sample_product_data)
    db_session.add(product)
    db_session.commit()

    saved = db_session.query(Product).filter(Product.name == "Notebook Pro X").first()
    assert saved is not None
    assert saved.id is not None
    assert saved.price == 14999.00
    assert "RTX 4070" in saved.description

def test_create_and_query_support_ticket(db_session, sample_ticket_data):
    """Testa criação e consulta de tickets de suporte."""
    ticket = SupportTicket(**sample_ticket_data)
    db_session.add(ticket)
    db_session.commit()

    saved = db_session.query(SupportTicket).filter(SupportTicket.ticket_number == "TCK-999").first()
    assert saved is not None
    assert saved.category == "troca"
    assert saved.status == "RESOLVED"

def test_task_result_lifecycle(db_session):
    """Testa persistência e consulta do resultado das tarefas."""
    task_id = "test-task-12345"
    
    # 1. Cria resultado da tarefa
    task = TaskResult(
        task_id=task_id,
        query="Quero comprar uma cadeira",
        agent_response="Recomendamos a Cadeira Ergonômica Max Confort por R$ 1.299,90"
    )
    db_session.add(task)
    db_session.commit()

    queried = db_session.query(TaskResult).filter(TaskResult.task_id == task_id).first()
    assert queried is not None
    assert queried.task_id == task_id
    assert "Cadeira Ergonômica" in queried.agent_response

def test_sql_injection_safety(db_session):
    """Testa imunidade a SQL Injection nas consultas com SQLAlchemy ORM."""
    malicious_task_id = "' OR '1'='1"
    
    # Consulta usando SQLAlchemy parametrizado
    result = db_session.query(TaskResult).filter(TaskResult.task_id == malicious_task_id).first()
    
    # Deve retornar None com segurança, sem quebrar a query ou vazar dados
    assert result is None
