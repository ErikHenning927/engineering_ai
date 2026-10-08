import logging
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.core.config import OPENAI_API_KEY, QDRANT_URL, LITELLM_URL
from ai_common.qdrant import search_similar_vectors
from ai_common.judge import LLMJudge
from ai_common.telemetry import get_langfuse_handler


logger = logging.getLogger("worker-recommendation.agent")

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

def process_recommendation(query: str, parameters: dict = None, task_id: str = "unknown") -> str:
    """
    Agente Especialista Recomendador de Produtos e Vendas.
    """
    logger.info(f"🛒 [Product Agent] Iniciando busca vetorial para: '{query}' (Task ID: {task_id})")
    handler = get_langfuse_handler(task_id)
    callbacks = [handler] if handler else []
    
    # 1. Busca Vetorial no Qdrant
    vector = embeddings.embed_query(query)
    recommendations = search_similar_vectors(QDRANT_URL, "products", vector, limit=2)
    
    if not recommendations:
        return "Nenhum produto encontrado no catálogo."
        
    logger.info(f"🛒 [Product Agent] {len(recommendations)} produtos similares encontrados. Gerando resposta com GPT-4o...")
    
    # 2. Geração da Resposta Comercial
    prompt = PromptTemplate.from_template(
        "Baseado nestes produtos reais: {produtos}, formule a melhor recomendação para o cliente: {query}"
    )
    chain = prompt | llm
    
    response = chain.invoke(
        {"produtos": recommendations, "query": query},
        config={"callbacks": callbacks, "run_name": "GeracaoRecomendacao", "metadata": {"task_id": task_id}}
    )
    
    # 3. Auditoria Centralizada LLM-as-a-Judge com Telemetria no Langfuse (ai_common)
    is_valid, final_text = judge.evaluate(
        context=recommendations,
        candidate_response=response.content,
        task_id=task_id,
        query=query,
        langfuse_handler=handler,
        fallback_message="Desculpe, por questões de conformidade e segurança, não consegui validar os preços ou especificações desta recomendação.",
        run_name="Product-LLM-as-a-Judge"
    )
    
    return final_text
