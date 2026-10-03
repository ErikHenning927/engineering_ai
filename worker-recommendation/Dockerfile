FROM python:3.11-slim

WORKDIR /app

# Instalar dependências de sistema (psycopg2 precisa de libpq-dev)
RUN apt-get update && apt-get install -y build-essential libpq-dev curl

# Instalando as dependências do worker
RUN pip install --no-cache-dir confluent-kafka python-dotenv qdrant-client psycopg2-binary sqlalchemy alembic "langchain<0.3.0" "langchain-core<0.3.0" "langchain-openai<0.2.0" "langfuse<3.0.0"

COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "-m", "app.main"]
