import logging
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.core.config import OPENAI_API_KEY, LITELLM_URL, QDRANT_URL
from ai_common.qdrant import search_similar_vectors
from ai_common.judge import LLMJudge
from ai_common.telemetry import get_langfuse_handler


logger = logging.getLogger("worker-assistant.agent")

DUMMY_KEY = "sk-any-key"

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# LLM Principal (Roteado via LiteLLM)
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2,
    openai_api_key=DUMMY_KEY,
    openai_api_base=LITELLM_URL
)

# LLM Juiz Centralizado (ai_common)
judge = LLMJudge(model="gpt-4o-mini", litellm_url=LITELLM_URL)
langfuse_handler = None  # Compatibilidade de import

def process_assistant_request(query: str, parameters: dict = None, task_id: str = "unknown") -> str:
    """
    Agente Especialista Assistente e Suporte / Trocas.
    """
    logger.info(f"🤖 [Assistant Agent] Processando requisição para Task ID {task_id}: '{query}'")
    handler = get_langfuse_handler(task_id)
    callbacks = [handler] if handler else []
    
    # 1. Busca semântica de contexto na coleção dedicada de suporte (Tickets & Manuais)
    vector = embeddings.embed_query(query)
    context_items = search_similar_vectors(QDRANT_URL, "support_knowledge", vector, limit=3)
    logger.info(f"🔍 [Assistant Agent] {len(context_items)} itens de suporte/tickets encontrados.")
    
    # 2. Prompt do Especialista Assistente Técnico & Suporte
    prompt_template = PromptTemplate.from_template(
        "Você é o Assistente Técnico Especialista em Atendimento, Suporte, Garantia e Troca de Produtos.\n"
        "Seu objetivo é ajudar o cliente com dúvidas técnicas, procedimentos de troca, orientações de garantia e suporte.\n\n"
        "Base de Conhecimento e Tickets Técnicos Disponíveis:\n{contexto}\n\n"
        "Solicitação do Cliente: {query}\n\n"
        "Forneça uma resposta clara, prestativa e profissional em português, explicando o passo a passo da solução ou orientações de garantia com base no histórico de atendimento."
    )
    
    chain = prompt_template | llm
    response = chain.invoke(
        {"contexto": context_items, "query": query},
        config={"callbacks": callbacks, "run_name": "AssistantServiceExecution", "metadata": {"task_id": task_id}}
    )
    
    # 3. Auditoria Centralizada LLM-as-a-Judge com Telemetria no Langfuse (ai_common)
    is_valid, final_text = judge.evaluate(
        context=context_items,
        candidate_response=response.content,
        task_id=task_id,
        query=query,
        langfuse_handler=handler,
        fallback_message="Desculpe, nossa auditoria automática identificou uma inconsistência com a base de suporte. Por favor, reformule sua solicitação.",
        run_name="Assistant-LLM-as-a-Judge"
    )
    
    return final_text
