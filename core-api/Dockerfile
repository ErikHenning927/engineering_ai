FROM python:3.11-slim

WORKDIR /app

# Instalar dependências de sistema necessárias
RUN apt-get update && apt-get install -y build-essential curl

# Copiar requirements se houver, ou instalar pacotes diretamente
# Copiar o requirements.txt e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8001
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "-m", "app.main"]
