from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.core.config import OPENAI_API_KEY
from app.db.qdrant_client import search_similar_products

import os

# Apontamos para o nosso container do LiteLLM (porta 4000)
LITELLM_BASE_URL = os.getenv("LITELLM_URL", "http://127.0.0.1:4000")
DUMMY_KEY = "sk-any-key" # O LiteLLM já tem as chaves reais

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY) # Embeddings mantém direto ou via proxy

# LLM Principal (Roteado para gpt-4o via LiteLLM)
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2, 
    openai_api_key=DUMMY_KEY, 
    openai_api_base=LITELLM_BASE_URL
)

# LLM Juiz (Usaremos o gpt-4o que sabemos que a sua chave tem permissão)
judge_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.0,
    openai_api_key=DUMMY_KEY,
    openai_api_base=LITELLM_BASE_URL
)

from langfuse.callback import CallbackHandler

# Tenta carregar as chaves do Langfuse (Você vai gerar isso na UI deles)
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

# Criação global do handler para que a thread de envio em background não morra
langfuse_handler = None
if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
    langfuse_handler = CallbackHandler()

def get_callbacks():
    if langfuse_handler:
        return [langfuse_handler]
    return []

def process_recommendation(query: str, task_id: str = "unknown"):
    print(f"[Agente] Iniciando busca vetorial para: '{query}'")
    vector = embeddings.embed_query(query)
    
    recommendations = search_similar_products(vector)
    
    if not recommendations:
        return "Nenhum produto encontrado na base."
        
    print(f"[Agente] {len(recommendations)} produtos similares encontrados. Gerando resposta com GPT-4o...")
    
    # 1. Geração da Resposta
    prompt = PromptTemplate.from_template(
        "Baseado nestes produtos: {produtos}, responda à necessidade do cliente: {query}"
    )
    chain = prompt | llm
    
    # Executa passando o Callback do Langfuse para rastrear
    response = chain.invoke(
        {"produtos": recommendations, "query": query},
        config={"callbacks": get_callbacks(), "run_name": "GeracaoRecomendacao", "metadata": {"task_id": task_id}}
    )
    
    # 2. LLM-as-a-Judge (Avaliação Crítica)
    print(f"[Judge] Validando a resposta gerada usando Gemini-Flash...")
    judge_prompt = PromptTemplate.from_template(
        "Você é um auditor rigoroso avaliando um agente de vendas.\n"
        "Base de Produtos Real: {produtos}\n"
        "Resposta do Agente: {resposta}\n"
        "A resposta do agente inventou algum produto ou preço que não está na base real? Responda APENAS com 'PASS' (se estiver tudo certo) ou 'FAIL' (se houve alucinação)."
    )
    judge_chain = judge_prompt | judge_llm
    judge_result = judge_chain.invoke(
        {"produtos": recommendations, "resposta": response.content},
        config={"callbacks": get_callbacks(), "run_name": "LLM-as-a-Judge"}
    )
    
    print(f"[Judge] Resultado Final da Auditoria: {judge_result.content}")
    
    if "FAIL" in judge_result.content.upper():
        print("⚠️ [ALERTA] Alucinação detectada pelo LLM Juiz! Bloqueando resposta.")
        if langfuse_handler:
            langfuse_handler.flush()
        return "Desculpe, por questões de segurança, não consegui validar sua recomendação."

    if langfuse_handler:
        langfuse_handler.flush()
        
    return response.content
