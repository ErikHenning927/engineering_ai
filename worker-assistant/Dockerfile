FROM python:3.11-slim

WORKDIR /app

# Instalar dependências de sistema
RUN apt-get update && apt-get install -y build-essential libpq-dev curl

# Instalar requirements do serviço
COPY worker-assistant/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Instalar o pacote compartilhado ai_common
COPY packages/ai_common /packages/ai_common
RUN pip install --no-cache-dir -e /packages/ai_common

COPY worker-assistant /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/packages

CMD ["python", "-u", "-m", "app.main"]
