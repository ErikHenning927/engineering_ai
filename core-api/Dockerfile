FROM python:3.11-slim

WORKDIR /app

# Instalar dependências de sistema necessárias
RUN apt-get update && apt-get install -y build-essential curl

# Copiar requirements se houver, ou instalar pacotes diretamente
# (Como não criamos requirements.txt fixo, instalamos os essenciais)
RUN pip install --no-cache-dir fastapi uvicorn confluent-kafka python-dotenv pydantic python-multipart

COPY . /app

EXPOSE 8001
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "-m", "app.main"]
