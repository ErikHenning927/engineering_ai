import os
import logging
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.core.config import OPENAI_API_KEY, LITELLM_URL, QDRANT_URL
from ai_common.qdrant import search_similar_vectors

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

# LLM Juiz / Auditor
judge_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.0,
    openai_api_key=DUMMY_KEY,
    openai_api_base=LITELLM_URL
)

# Langfuse Telemetria
from langfuse.callback import CallbackHandler

LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

langfuse_handler = None
if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
    langfuse_handler = CallbackHandler()

def get_callbacks():
    if langfuse_handler:
        return [langfuse_handler]
    return []

def process_assistant_request(query: str, parameters: dict = None, task_id: str = "unknown") -> str:
    """
    Agente Especialista Assistente e Suporte / Trocas:
    Analisa a dúvida técnica, solicitação de troca ou suporte do cliente,
    executa busca vetorial na base de conhecimento e histórico de tickets
    e formula uma resposta técnica estruturada.
    """
    logger.info(f"🤖 [Assistant Agent] Processando requisição para Task ID {task_id}: '{query}'")
    
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
        config={"callbacks": get_callbacks(), "run_name": "AssistantServiceExecution", "metadata": {"task_id": task_id}}
    )
    
    # 3. LLM-as-a-Judge (Auditoria do Assistente)
    logger.info(f"⚖️ [Judge] Auditando a resposta do Assistente...")
    judge_prompt = PromptTemplate.from_template(
        "Você é um auditor de qualidade de atendimento técnico de IA.\n"
        "Base de Contexto Real: {contexto}\n"
        "Resposta do Assistente: {resposta}\n"
        "A resposta do assistente é segura, coerente e não contradiz o contexto? Responda APENAS com 'PASS' ou 'FAIL'."
    )
    judge_chain = judge_prompt | judge_llm
    judge_result = judge_chain.invoke(
        {"contexto": context_items, "resposta": response.content},
        config={"callbacks": get_callbacks(), "run_name": "Assistant-LLM-as-a-Judge"}
    )
    
    logger.info(f"⚖️ [Judge] Resultado da Auditoria: {judge_result.content}")
    
    if "FAIL" in judge_result.content.upper():
        logger.warning("⚠️ [ALERTA] Violação detectada pelo LLM Juiz na resposta do Assistente.")
        if langfuse_handler:
            langfuse_handler.flush()
        return "Desculpe, nossa auditoria automática identificou uma inconsistência. Por favor, reformule sua solicitação."

    if langfuse_handler:
        langfuse_handler.flush()
        
    return response.content
