from fastapi import APIRouter, Form
from app.agent.orchestrator import process_with_langgraph

router = APIRouter()

@router.post("/orchestrate")
async def orchestrate(query: str = Form(...)):
    # Agora o orquestrador não recebe mais um "intent" manual!
    # O usuário envia apenas a 'query', e o LangGraph resolve todo o resto.
    result = process_with_langgraph(query)
    
    return result
