import os
import logging
from typing import Optional, List
try:
    from langfuse.callback import CallbackHandler
except (ImportError, ModuleNotFoundError):
    CallbackHandler = None


logger = logging.getLogger("ai_common.telemetry")

LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")

def get_langfuse_handler(task_id: str, user_id: str = "cliente-api") -> Optional[CallbackHandler]:
    """
    Cria um handler dedicado do Langfuse por tarefa/sessão para evitar mistura de traces.
    """
    if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
        try:
            return CallbackHandler(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
                host=LANGFUSE_HOST,
                session_id=task_id,
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Não foi possível inicializar o CallbackHandler do Langfuse: {e}")
            return None
    return None

def record_judge_telemetry(
    handler: Optional[CallbackHandler],
    is_fail: bool,
    task_id: str = "",
    query: str = "",
    verdict: str = "PASS",
    details: str = ""
):
    """
    Registra tags visuais e score de alucinação padronizados no Langfuse.
    """
    if not handler:
        return
        
    try:
        trace_id = handler.get_trace_id()
        if trace_id:
            # 1. Tags padronizadas para filtros rápidos no dashboard
            tags = ["hallucination", "judge_fail", "needs_review"] if is_fail else ["judge_pass", "verified"]
            
            handler.langfuse.trace(
                id=trace_id,
                tags=tags,
                metadata={
                    "task_id": task_id,
                    "query": query,
                    "judge_verdict": verdict,
                    "details": details
                }
            )
            
            # 2. Score numérico (0.0 = alucinação / 1.0 = aprovado)
            handler.langfuse.score(
                trace_id=trace_id,
                name="hallucination",
                value=0.0 if is_fail else 1.0,
                comment=f"🚨 ALUCINAÇÃO DETECTADA: {details}" if is_fail else f"✅ PASS: {details or 'Resposta factual e validada'}"
            )
        handler.flush()
    except Exception as e:
        logger.warning(f"Erro ao registrar score no Langfuse: {e}")
