# Microserviço de Inteligência RAG - Recomendação de Trocas de Produtos (`microservice-ai`)

Este microserviço é a camada de **Inteligência Artificial e RAG (Retrieval-Augmented Generation)** responsável por recomendar produtos similares para troca (garantia, avaria ou indisponibilidade de estoque).

Ele se conecta ao **DW SQL Server** para obter dados de cadastro mestre dos produtos (`dim_item`), gera embeddings de alta dimensão com a API da **OpenAI (`text-embedding-3-small`)** e gerencia o armazenamento e as buscas vetoriais por similaridade de cosseno no **Qdrant**.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem**: Python 3.11+
- **Framework Web**: FastAPI + Uvicorn
- **Banco de Dados de Origem**: DW SQL Server (via `pymssql`)
- **Banco Vetorial**: Qdrant (via `qdrant-client` integrado com container local docker)
- **OpenAI SDK**: Geração de Embeddings (`text-embedding-3-small`) e LLM (`gpt-4o-mini`)

---

## 📐 Arquitetura RAG de Recomendações

```
┌─────────────────────────────────┐
│ Pergunta ou Código do Produto   │ (ex: "Troca para o liquidificador 025013S")
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│     FastAPI (POST /rag/ask)     │
└────────────────┬────────────────┘
                 │ 1. Valida o código do item contra o SQL Server DW
                 │ 2. Gera o vetor de busca via OpenAI API
                 ▼
┌─────────────────────────────────┐
│             Qdrant              │ 3. Executa a busca vetorial aplicando
│      (Coleção de Produtos)      │    filtros rígidos de voltagem e grupo comercial
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│      OpenAI GPT Completion      │ 4. Recebe a lista de candidatos e formata
│   (Geração de Recomendação)     │    a resposta e o JSON estruturado para o app
└─────────────────────────────────┘
```

---

## 📁 Estrutura de Pastas

```
project-at-rag-products/
├── docker-compose.yml       # Orquestração do serviço Qdrant
├── tests/                   # Testes e scripts de validação
│   ├── test_conn.py         # Validação de conexão com SQL Server DW
│   ├── test_check_counts.py # Validação volumétrica de dim_item
│   ├── test_openai_qdrant.py# Teste unitário OpenAI e Qdrant
│   └── test_rag_pipeline.py # Teste fim a fim do fluxo de RAG
└── microservice-ai/
    ├── src/
    │   ├── main.py          # Inicialização FastAPI, CORS e lifespans
    │   ├── config.py        # Configurações do app (.env) e segurança de portas
    │   ├── database.py      # Conectividade SQL Server DW (pymssql)
    │   └── rag/
    │       ├── router.py    # Definições de endpoints da API FastAPI
    │       ├── service.py   # Lógica principal RAGProductService
    │       ├── embeddings.py# API OpenAI para geração de embeddings
    │       ├── qdrant_client.py# Inicialização e controle do cliente Qdrant
    │       └── schema_dict.py  # Metadados estáticos do e-commerce
    ├── requirements.txt     # Dependências Python
    └── .env                 # Credenciais locais
```

---

## 🚀 Como Rodar

### 1. Iniciar o Banco Vetorial Qdrant
Inicie o container do Qdrant a partir da pasta raiz do projeto:
```bash
docker compose up -d
```
O Qdrant Dashboard estará disponível no navegador em `http://localhost:6333/dashboard`.

### 2. Configurar o Ambiente Virtual
Na pasta raiz do projeto, ative o ambiente virtual e instale as dependências:
```bash
source .venv/bin/activate
pip install -r microservice-ai/requirements.txt pymssql qdrant-client
```

### 3. Configurar as Variáveis de Ambiente
Verifique as credenciais no arquivo `microservice-ai/.env`:
```env
OPENAI_API_KEY=sk-proj-...
EMBEDDING_MODEL=text-embedding-3-small
COMPLETION_MODEL=gpt-4o-mini

# Credenciais DW SQL Server
DW_HOST=10.0.10.188
DW_PORT=1433
DW_USER=svc.cadastropecasat
DW_PASSWORD=...
DW_NAME=DW

# Configurações Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=products
```

### 4. Rodar o FastAPI
Navegue até a pasta `microservice-ai` e inicie o uvicorn:
```bash
cd microservice-ai
uvicorn src.main:app --host 0.0.0.0 --port 8002 --reload
```

---

## 📡 Endpoints da API

### `POST /rag/index-products`
Busca os produtos de `dim_item` no SQL Server DW, gera embeddings e insere no Qdrant.
- **Body de requisição:**
  ```json
  {
    "limit": 500,
    "only_finished": true,
    "group_filter": "VENTILADORES"
  }
  ```

### `POST /rag/recommend-products`
Busca produtos similares e equivalentes no Qdrant aplicando filtros comerciais de voltagem e grupo.
- **Body de requisição:**
  ```json
  {
    "query_or_code": "025013S",
    "limit": 5,
    "match_voltage": true,
    "match_group": true
  }
  ```

### `POST /rag/ask`
Recebe o prompt ou dúvida do usuário, extrai e valida códigos de produtos e gera uma resposta de recomendação de troca estruturada.
- **Body de requisição:**
  ```json
  {
    "query_prompt": "Sugira uma troca para o produto 025013S de 110v",
    "limit": 5,
    "response_format": "list"
  }
  ```
