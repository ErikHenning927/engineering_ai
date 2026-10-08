#!/usr/bin/env python
"""
🛠️ Agent Scaffolder CLI - Enterprise Multi-Agent Platform
Cria a estrutura completa de um novo microserviço Worker Especialista padronizado com ai_common,
Dockerfile, requirements, configuração, agente com LLMJudge e testes automatizados.
"""

import os
import sys
import argparse
import re

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DOCKERFILE_TEMPLATE = """FROM python:3.11-slim

WORKDIR /app

# Instalar dependências de sistema (psycopg2 precisa de libpq-dev)
RUN apt-get update && apt-get install -y build-essential libpq-dev curl

# Instalar requirements do serviço
COPY {folder_name}/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Instalar o pacote compartilhado ai_common
COPY packages/ai_common /packages/ai_common
RUN pip install --no-cache-dir -e /packages/ai_common

COPY {folder_name} /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/packages

CMD ["python", "-u", "-m", "app.main"]
"""

REQUIREMENTS_TEMPLATE = """fastapi
confluent-kafka
python-dotenv
langchain
langchain-openai
pydantic
sqlalchemy
psycopg2-binary
qdrant-client
langfuse
pytest
pytest-asyncio
pytest-mock
"""

CONFIG_TEMPLATE = """import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+psycopg2://ai_user:ai_password@postgres:5432/ai_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
LITELLM_URL = os.getenv("LITELLM_URL", "http://litellm:4000")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Configurações do Consumidor Kafka
TOPIC_NAME = os.getenv("{upper_name}_TOPIC", "{name}_tasks")
GROUP_ID = os.getenv("{upper_name}_GROUP_ID", "{name}_agent_group")
DLQ_TOPIC = os.getenv("{upper_name}_DLQ_TOPIC", "{name}_tasks_dlq")

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "2.0"))
"""

AGENT_TEMPLATE = """import logging
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.core.config import OPENAI_API_KEY, QDRANT_URL, LITELLM_URL
from ai_common.qdrant import search_similar_vectors
from ai_common.judge import LLMJudge
from ai_common.telemetry import get_langfuse_handler

logger = logging.getLogger("{folder_name}.agent")
DUMMY_KEY = "sk-any-key"

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# LLM de Geração Roteado via LiteLLM
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2,
    openai_api_key=DUMMY_KEY,
    openai_api_base=LITELLM_URL
)

# LLM-as-a-Judge Centralizado (ai_common)
judge = LLMJudge(model="gpt-4o-mini", litellm_url=LITELLM_URL)
langfuse_handler = None

def process_{name}_task(query: str, parameters: dict = None, task_id: str = "unknown") -> str:
    \"\"\"
    {display_name} - {description}
    \"\"\"
    logger.info(f"🤖 [{display_name}] Processando query: '{{query}}' (Task ID: {{task_id}})")
    handler = get_langfuse_handler(task_id)
    callbacks = [handler] if handler else []

    # 1. Recuperação Vetorial de Contexto no Qdrant
    vector = embeddings.embed_query(query)
    context_data = search_similar_vectors(QDRANT_URL, "{name}_knowledge", vector, limit=2)

    # 2. Geração da Resposta com Prompt Especializado
    prompt = PromptTemplate.from_template(
        \"\"\"Você é o {display_name}.
Contexto oficial disponível:
{{context}}

Pergunta do usuário:
{{query}}

Instruções: Responda de forma precisa, objetiva e estritamente baseada no contexto oficial acima. Nunca invente regras ou dados.\"\"\"
    )
    chain = prompt | llm

    response = chain.invoke(
        {{"context": context_data or "Nenhum documento específico encontrado.", "query": query}},
        config={{"callbacks": callbacks, "run_name": "{class_name}Generation", "metadata": {{"task_id": task_id}}}}
    )

    # 3. Auditoria LLM-as-a-Judge contra alucinações
    is_valid, final_text = judge.evaluate(
        context=context_data or [],
        candidate_response=response.content,
        task_id=task_id,
        query=query,
        langfuse_handler=handler,
        fallback_message="Desculpe, nossa auditoria identificou inconsistências com a base oficial de {name}. Por favor, consulte o suporte humano.",
        run_name="{class_name}-Judge"
    )

    return final_text
"""

MAIN_TEMPLATE = """import logging
from ai_common.kafka.base_consumer import BaseKafkaWorker
from app.core.config import (
    KAFKA_BROKER,
    TOPIC_NAME,
    GROUP_ID,
    DLQ_TOPIC,
    MAX_RETRIES,
    RETRY_BASE_DELAY
)
from app.agent.{name}_agent import process_{name}_task, langfuse_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

class {class_name}Worker(BaseKafkaWorker):
    def __init__(self):
        super().__init__(
            worker_name="{display_name}",
            bootstrap_servers=KAFKA_BROKER,
            topic=TOPIC_NAME,
            group_id=GROUP_ID,
            dlq_topic=DLQ_TOPIC,
            max_retries=MAX_RETRIES,
            retry_base_delay=RETRY_BASE_DELAY,
            langfuse_handler=langfuse_handler
        )

    def process_task(self, query: str, task_data: dict) -> str:
        task_id = task_data.get("task_id", "unknown")
        return process_{name}_task(query, task_id=task_id)

if __name__ == "__main__":
    worker = {class_name}Worker()
    worker.run()
"""

TEST_TEMPLATE = """import importlib.util
import os
import pytest
from unittest.mock import MagicMock, patch

def load_module(module_name, rel_path):
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), rel_path)),
        f"/workspace/{{rel_path.replace('../../', '')}}"
    ]
    file_path = next((p for p in possible_paths if os.path.exists(p)), None)
    assert file_path is not None, f"Arquivo {{rel_path}} não encontrado."
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_{name}_worker_structure():
    config = load_module("{name}_config", "../../{folder_name}/app/core/config.py")
    assert config.TOPIC_NAME == "{name}_tasks"
    assert config.GROUP_ID == "{name}_agent_group"

def test_{name}_agent_execution_with_mock():
    with patch("langchain_openai.OpenAIEmbeddings.embed_query", return_value=[0.1]*1536):
        with patch("ai_common.qdrant.search_similar_vectors", return_value=[{{"title": "Doc Exemplo", "solution": "Solucao"}}]):
            with patch("ai_common.judge.LLMJudge.evaluate", return_value=(True, "Resposta aprovada com sucesso")):
                agent_mod = load_module("{name}_agent", "../../{folder_name}/app/agent/{name}_agent.py")
                res = agent_mod.process_{name}_task("Consulta de teste", task_id="test-123")
                assert "Resposta aprovada" in res
"""

def create_agent(name: str, display_name: str, description: str, prototypes: list[str] = None):
    slug = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower()).strip('_')
    folder_name = f"worker-{slug}"
    class_name = "".join(word.capitalize() for word in slug.split("_"))
    upper_name = slug.upper()

    target_dir = os.path.join(ROOT_DIR, folder_name)
    if os.path.exists(target_dir):
        print(f"❌ Erro: O diretório '{folder_name}' já existe!")
        return False

    print(f"🚀 Criando novo Agente Especialista: '{display_name}' ({folder_name})...")

    # 1. Criar estrutura de diretórios
    os.makedirs(os.path.join(target_dir, "app", "core"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "app", "agent"), exist_ok=True)

    # 2. Escrever Dockerfile
    with open(os.path.join(target_dir, "Dockerfile"), "w", encoding="utf-8") as f:
        f.write(DOCKERFILE_TEMPLATE.format(folder_name=folder_name))

    # 3. Escrever requirements.txt
    with open(os.path.join(target_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write(REQUIREMENTS_TEMPLATE)

    # 4. Escrever arquivos Python
    open(os.path.join(target_dir, "app", "__init__.py"), "w").close()
    open(os.path.join(target_dir, "app", "core", "__init__.py"), "w").close()
    open(os.path.join(target_dir, "app", "agent", "__init__.py"), "w").close()

    with open(os.path.join(target_dir, "app", "core", "config.py"), "w", encoding="utf-8") as f:
        f.write(CONFIG_TEMPLATE.format(upper_name=upper_name, name=slug))

    with open(os.path.join(target_dir, "app", "agent", f"{slug}_agent.py"), "w", encoding="utf-8") as f:
        f.write(AGENT_TEMPLATE.format(
            folder_name=folder_name,
            name=slug,
            display_name=display_name,
            description=description,
            class_name=class_name
        ))

    with open(os.path.join(target_dir, "app", "main.py"), "w", encoding="utf-8") as f:
        f.write(MAIN_TEMPLATE.format(
            display_name=display_name,
            name=slug,
            class_name=class_name
        ))

    # 5. Criar Teste Unitário
    test_path = os.path.join(ROOT_DIR, "tests", "unit", f"test_worker_{slug}.py")
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(TEST_TEMPLATE.format(name=slug, folder_name=folder_name))

    print(f"✅ Diretório '{folder_name}' criado com sucesso!")
    print(f"✅ Dockerfile, requirements.txt, config.py e {slug}_agent.py gerados.")
    print(f"✅ Teste unitário criado em: tests/unit/test_worker_{slug}.py")

    # 6. Exibir snippet do docker-compose
    compose_snippet = f"""
  # ----------------------------------------
  # Novo Worker: {display_name}
  # ----------------------------------------
  worker_{slug}:
    build:
      context: .
      dockerfile: {folder_name}/Dockerfile
    container_name: worker_{slug}
    volumes:
      - ./{folder_name}:/app
      - ./packages/ai_common:/packages/ai_common
    environment:
      - KAFKA_BROKER=kafka:9092
      - POSTGRES_URL=postgresql+psycopg2://ai_user:ai_password@postgres:5432/ai_db
      - QDRANT_URL=http://qdrant:6333
      - LITELLM_URL=http://litellm:4000
      - LANGFUSE_HOST=http://langfuse:3000
      - PYTHONPATH=/app:/packages
    depends_on:
      - kafka
      - postgres
      - qdrant
      - litellm
    env_file:
      - .env
"""
    print("\n📦 [Snippet para docker-compose.yml]:")
    print(compose_snippet)

    return True

def main():
    parser = argparse.ArgumentParser(description="CLI Scaffolder para novos Agentes Especialistas de IA")
    parser.add_argument("--name", help="Slug do agente (ex: billing, logistics, crm)")
    parser.add_argument("--display-name", help="Nome de exibição (ex: 'Worker Financeiro e Faturamento')")
    parser.add_argument("--description", help="Descrição do escopo de atuação do agente")
    parser.add_argument("--prototypes", help="Frases de exemplo separadas por vírgula para o Vector Router")

    args = parser.parse_args()

    if not args.name:
        print("🤖 Bem-vindo ao Agent Scaffolder CLI!")
        name = input("👉 Digite o identificador único do agente (ex: billing, logistics, sql_analyst): ").strip()
        display_name = input("👉 Digite o nome de exibição (ex: Worker Especialista em Faturamento): ").strip()
        description = input("👉 Digite uma breve descrição do escopo: ").strip()
        prototypes_raw = input("👉 Digite exemplos de perguntas (separadas por vírgula): ").strip()
        prototypes = [p.strip() for p in prototypes_raw.split(",") if p.strip()]
    else:
        name = args.name
        display_name = args.display_name or f"Worker {name.capitalize()}"
        description = args.description or f"Agente Especialista em {name}"
        prototypes = [p.strip() for p in (args.prototypes or "").split(",") if p.strip()]

    create_agent(name, display_name, description, prototypes)

if __name__ == "__main__":
    main()
