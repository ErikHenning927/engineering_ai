import json
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from app.agent.orchestrator import process_with_langgraph
from ai_common.db.session import get_db
from ai_common.db.models import TaskResult

logger = logging.getLogger("core-api.routes")
router = APIRouter()

class OrchestrateRequest(BaseModel):
    query: str = Field(..., description="A mensagem, pergunta ou pedido do usuário", example="Notebook Pro X")

class TaskResponse(BaseModel):
    task_id: str
    status: str
    query: Optional[str] = None
    result: Optional[str] = None
    created_at: Optional[datetime] = None
    message: Optional[str] = None

@router.post("/orchestrate")
async def orchestrate(request: Request):
    """
    Ponto de entrada assíncrono do Orquestrador LangGraph.
    Resiliente a qualquer formato de cliente (JSON, Raw JSON String, Form, etc.).
    """
    query_str = None
    
    # 1. Tenta interpretar como JSON
    try:
        body_data = await request.json()
        if isinstance(body_data, dict):
            query_str = body_data.get("query")
        elif isinstance(body_data, str):
            try:
                parsed = json.loads(body_data)
                if isinstance(parsed, dict):
                    query_str = parsed.get("query")
                else:
                    query_str = body_data
            except Exception:
                query_str = body_data
    except Exception:
        pass

    # 2. Se não encontrou, tenta interpretar como Form
    if not query_str:
        try:
            form = await request.form()
            query_str = form.get("query")
        except Exception:
            pass

    # 3. Fallback: lê os bytes brutos do corpo
    if not query_str:
        try:
            raw_bytes = await request.body()
            decoded = raw_bytes.decode('utf-8').strip()
            if decoded:
                if decoded.startswith("{") and decoded.endswith("}"):
                    try:
                        parsed = json.loads(decoded)
                        if isinstance(parsed, dict):
                            query_str = parsed.get("query")
                    except Exception:
                        pass
                if not query_str:
                    query_str = decoded
        except Exception:
            pass

    if not query_str or not str(query_str).strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O campo 'query' é obrigatório no corpo da requisição (ex: {\"query\": \"Notebook Pro X\"})."
        )

    clean_query = str(query_str).strip()
    result = await process_with_langgraph(clean_query)
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
