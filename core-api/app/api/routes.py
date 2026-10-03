import uuid
from fastapi import APIRouter, Form
from app.services.kafka_producer import publish_task
from app.core.config import PRODUCT_TOPIC

router = APIRouter()

@router.post("/orchestrate")
async def orchestrate(intent: str = Form(...), query: str = Form(None)):
    task_id = str(uuid.uuid4())
    
    if intent == "recommend":
        task_data = {
            "task_id": task_id,
            "query": query,
            "intent": intent
        }
        # Apenas publica na fila e libera a conexão HTTP imediatamente
        publish_task(PRODUCT_TOPIC, task_data)
        
        return {
            "status": "processing",
            "task_id": task_id,
            "message": "Tarefa enviada para a fila do Agente de Recomendação."
        }
    
    return {"status": "error", "message": "Intenção não suportada."}
