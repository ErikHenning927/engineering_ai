from typing import Optional, List
from fastapi import APIRouter, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.agent.orchestrator import process_with_langgraph
from ai_common.db.session import get_db
from ai_common.db.models import TaskResult

router = APIRouter()

class TaskResponse(BaseModel):
    task_id: str
    status: str
    query: Optional[str] = None
    result: Optional[str] = None
    created_at: Optional[datetime] = None
    message: Optional[str] = None

@router.post("/orchestrate")
async def orchestrate(query: str = Form(...)):
    """
    Ponto de entrada assíncrono do Orquestrador LangGraph.
    Não bloqueia o Event Loop do FastAPI.
    """
    result = await process_with_langgraph(query)
    return result

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """
    Endpoint de consulta de status (Polling / Async UX):
    Permite ao cliente verificar se a tarefa assíncrona despachada
    para o Worker já foi processada e gravada no PostgreSQL.
    """
    task = db.query(TaskResult).filter(TaskResult.task_id == task_id).first()
    
    if task:
        return TaskResponse(
            task_id=task.task_id,
            status="completed",
            query=task.query,
            result=task.agent_response,
            created_at=task.created_at,
            message="Tarefa processada com sucesso pelo Agente Especialista."
        )
    
    # Se ainda não estiver no banco, a tarefa está na fila ou sendo executada pelo worker
    return TaskResponse(
        task_id=task_id,
        status="processing",
        message="A tarefa está na fila de execução ou sendo processada pelo Worker Especialista."
    )

@router.get("/tasks", response_model=List[TaskResponse])
async def list_recent_tasks(limit: int = 20, db: Session = Depends(get_db)):
    """
    Lista as tarefas mais recentes processadas pelos Workers.
    """
    tasks = db.query(TaskResult).order_by(TaskResult.created_at.desc()).limit(limit).all()
    return [
        TaskResponse(
            task_id=t.task_id,
            status="completed",
            query=t.query,
            result=t.agent_response,
            created_at=t.created_at
        )
        for t in tasks
    ]
