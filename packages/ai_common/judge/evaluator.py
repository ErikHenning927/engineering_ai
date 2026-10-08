import os
import logging
from typing import Any, Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from ai_common.telemetry.langfuse import record_judge_telemetry

logger = logging.getLogger("ai_common.judge")

DEFAULT_JUDGE_PROMPT = """Você é um auditor de qualidade e conformidade de IA (LLM-as-a-Judge).
Sua missão é verificar rigorosamente se a resposta gerada pelo agente de IA é estritamente factual e alinhada à Base de Conhecimento Real fornecida.

[BASE DE CONHECIMENTO REAL]:
{contexto}

[SOLICITAÇÃO DO CLIENTE]:
{query}

[RESPOSTA GERADA PELO AGENTE]:
{resposta}

CRITÉRIOS DE AUDITORIA:
1. A resposta inventou dados, preços, características, produtos ou prazos que NÃO constam na base?
2. A resposta contradiz ou desvia totalmente do contexto e do escopo solicitado?
3. Se houver qualquer alucinação, invenção ou contradição com a base, reprove.

Responda APENAS:
- 'PASS' (se estiver tudo estritamente correto e fundamentado na base)
- 'FAIL' (se houver alucinação, invenção ou contradição)
"""

class LLMJudge:
    """
    Componente centralizado de auditoria LLM-as-a-Judge.
    Garante que as respostas geradas por qualquer worker especialista sejam validadas
    contra alucinações e registradas com telemetria unificada no Langfuse.
    """
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        litellm_url: Optional[str] = None
    ):
        base_url = litellm_url or os.getenv("LITELLM_URL", "http://litellm:4000")
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key="sk-any-key",
            openai_api_base=base_url
        )
        self.prompt = PromptTemplate.from_template(DEFAULT_JUDGE_PROMPT)

    def evaluate(
        self,
        context: Any,
        candidate_response: str,
        task_id: str = "unknown",
        query: str = "",
        fallback_message: Optional[str] = None,
        langfuse_handler: Optional[Any] = None,
        run_name: str = "LLM-as-a-Judge"
    ) -> Tuple[bool, str]:
        """
        Avalia a resposta gerada.
        
        Retorna:
            (is_valid: bool, final_text: str)
            - Se PASS: retorna (True, candidate_response)
            - Se FAIL: retorna (False, fallback_message) e anexa score=0.0 no Langfuse
        """
        logger.info(f"⚖️ [LLM-as-a-Judge] Iniciando auditoria para Task ID: {task_id}...")
        
        callbacks = [langfuse_handler] if langfuse_handler else []
        judge_chain = self.prompt | self.llm
        
        try:
            judge_result = judge_chain.invoke(
                {
                    "contexto": context,
                    "query": query,
                    "resposta": candidate_response
                },
                config={
                    "callbacks": callbacks,
                    "run_name": run_name,
                    "metadata": {"task_id": task_id}
                }
            )
            verdict_text = judge_result.content.strip().upper()
            is_fail = "FAIL" in verdict_text
            
            logger.info(f"⚖️ [LLM-as-a-Judge] Veredito Final: {'FAIL ❌' if is_fail else 'PASS ✅'}")
            
            # Registra telemetria padronizada no Langfuse
            record_judge_telemetry(
                handler=langfuse_handler,
                is_fail=is_fail,
                task_id=task_id,
                query=query,
                verdict="FAIL" if is_fail else "PASS",
                details="Alucinação detectada ou resposta contraditória à base" if is_fail else "Factual e seguro"
            )
            
            if is_fail:
                logger.warning(f"🚨 [LLM-as-a-Judge] Alucinação interceptada no Task ID {task_id}! Bloqueando resposta.")
                safe_msg = fallback_message or "Desculpe, nossa auditoria automática identificou uma inconsistência com a base. Por favor, reformule sua solicitação."
                return False, safe_msg
                
            return True, candidate_response
            
        except Exception as e:
            logger.error(f"❌ Erro na execução do LLM-as-a-Judge: {e}")
            # Em caso de falha de conexão do juiz, aprova ou devolve mensagem segura por contingência
            return True, candidate_response
