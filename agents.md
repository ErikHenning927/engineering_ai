# 🤖 Arquitetura Multi-Agente & Orquestração Inteligente (AI Template)

Este documento descreve a arquitetura distribuída, event-driven e orientada a microsserviços desenvolvida para a plataforma de agentes de IA, incluindo as diretrizes de segurança, fluxo de dados, pacote compartilhado `ai_common`, governança com LLM-as-a-Judge e a suíte de testes automatizados.

---

## 🏛️ 1. Visão Geral da Arquitetura

A solução adota o padrão **Supervisor + Especialistas Desacoplados (Worker Agents)**, garantindo escalabilidade horizontal, isolamento de recursos e segurança multicamadas.

```
                    ┌────────────────────────────────────────────────────────┐
                    │                      CLIENTE                           │
                    │               (Swagger / API / Frontend)               │
                    └──────────────────────────┬─────────────────────────────┘
                                               │ HTTP POST /orchestrate
                                               ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                               CORE-API (API GATEWAY & SUPERVISOR)                         │
│                                                                                           │
│   [ Entrada ] ──► [ ⚡ Engine Concorrente: asyncio.gather ]                                │
│                          │                                                                │
│          ┌───────────────┴──────────────────────────────┐                                 │
│          ▼                                              ▼                                 │
│   [ 🛡️ Guardrail (gpt-4o-mini) ]         [ 🧠 Roteador Vetorial (Qdrant: routes_index) ]   │
│          │                                              │                                 │
│     (Se Ameaça)                                         │                                 │
│          ▼                                              ▼                                 │
│   [ ⛔ Security Block ]                           [ 🧭 Decisão de Rota ]                  │
│   (Retorna Bloqueio)                             ├── Intent: 'recommend' ─► [ 📦 Kafka ]  │
│                                                  ├── Intent: 'support'   ─► [ 🛠️ Kafka ]  │
│                                                  └── Intent: 'small_talk'─► [ 💬 Direto ] │
└────────────────────────────────────────────────────────────────┼──────────────────────────┘
                                                                 │ Publica Evento
                                                                 ▼
                                                    ┌─────────────────────────┐
                                                    │   APACHE KAFKA BROKER   │
                                                    │ (product_tasks / DLQ)   │
                                                    └────────────┬────────────┘
                                                                 │ Consome Mensagem
                                                                 ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                           WORKERS ESPECIALISTAS (AI COMMON)                               │
│                                                                                           │
│   [ BaseKafkaWorker ] ──► [ 🔍 Busca Vetorial (Qdrant) ] ──► [ 📝 Geração (GPT-4o) ]       │
│                                                                    │                      │
│                                                                    ▼                      │
│                                                       [ ⚖️ ai_common.judge.LLMJudge ]      │
│                                                                    │ (PASS / FAIL)        │
│                                                                    ▼                      │
│                     [ 💾 Salva em PostgreSQL ] ◄─── [ 🔭 Telemetria Langfuse Tags/Score ] │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 2. Componentes e Contêineres

| Contêiner | Tecnologia | Porta | Função Principal |
| :--- | :--- | :--- | :--- |
| `api_gateway` | FastAPI + LangGraph | `8001` | Gateway HTTP, Guardrail defensivo (`gpt-4o-mini`) e Roteador Semântico Vetorial via Qdrant. |
| `worker_recommendation` | Python + LangChain + `ai_common` | - | Consumidor Kafka especialista em vendas, catálogo e busca vetorial de produtos com LLM-as-a-Judge. |
| `worker_assistant` | Python + LangChain + `ai_common` | - | Consumidor Kafka especialista em suporte técnico, garantia, trocas e resolução de tickets. |
| `kafka_broker` | Apache Kafka (KRaft) | `9092` | Mensageria assíncrona tolerante a falhas com Dead Letter Queue (DLQ) e retries. |
| `litellm_proxy` | LiteLLM Proxy | `4000` | Gateway centralizador de chamadas a LLMs (balanceamento, fallbacks e rate limits). |
| `qdrant` | Qdrant Vector DB | `6333` | Banco vetorial para rotas (`routes_index`), catálogo (`products`) e tickets (`support_knowledge`). |
| `postgres_db` | PostgreSQL 16 | `5432` | Persistência relacional (`products`, `support_tickets`, `task_results`) e backend do Langfuse. |
| `langfuse` | Langfuse v2 | `3000` | Observabilidade em tempo real, traces, latência, custos e scores de alucinação (LLMOps). |

---

## 📚 3. O Pacote Compartilhado (`packages/ai_common`)

Todos os microserviços utilizam a biblioteca interna `ai_common` para garantir reutilização de código e padronização:

- **`ai_common.db`**: Modelos SQLAlchemy (`Product`, `SupportTicket`, `TaskResult`) e gerenciamento de sessões/conexões (compatível com PostgreSQL e SQLite in-memory para testes).
- **`ai_common.kafka`**:
  - `publish_task`: Produtor assíncrono para o Gateway HTTP (`aiokafka`).
  - `BaseKafkaWorker`: Consumidor padrão resiliente com Exponential Backoff (3 tentativas) e Graceful Shutdown (`SIGTERM`/`SIGINT`).
  - `DLQProducer`: Encaminhamento de falhas irrecuperáveis para a Dead Letter Queue (`tasks_dlq`).
- **`ai_common.qdrant`**: `VectorRouter` para classificação de intenções em `< 50ms` e gerenciador de busca vetorial.
- **`ai_common.judge`**: `LLMJudge` centralizado para auditoria automática pós-geração contra alucinações.
- **`ai_common.telemetry`**: `get_langfuse_handler` e `record_judge_telemetry` com gravação automática de tags (`hallucination`, `judge_fail`, `judge_pass`) e scores numéricos (`0.0` e `1.0`).

---

## 🛡️ 4. Camadas de Segurança (Prompt Injection & SQL Injection)

1. **Security Guardrail (Prompt Injection / Jailbreak):**
   - Executa no ponto de entrada do Supervisor com `gpt-4o-mini` e saída estruturada Pydantic (`SecurityEvaluation`).
   - Bloqueia comandos maliciosos, vazamento de chaves/prompts de sistema e jailbreaks (`DAN`), retornando HTTP 200 com `status: "blocked"` sem acionar o Kafka ou os bancos.
2. **Imunidade a SQL Injection:**
   - O sistema utiliza **SQLAlchemy ORM** com *Prepared Statements* parametrizados em 100% das consultas.
   - Nenhuma query é montada via concatenação manual de strings. Entradas maliciosas como `' OR '1'='1` são tratadas estritamente como strings literais inofensivas.

---

## 🧭 5. O Grafo do Orquestrador (`OrchestratorState`)

O supervisor em **LangGraph** opera com execução paralela para garantir latência ultra-baixa (~800ms a 1.2s):

1. **`entry_evaluator`:** 
   - Se o cliente informar `worker` (ex: `"assistant"`, `"recommend"`, `"billing"`), o Roteador Vetorial é pulado e apenas o `security_guardrail` (`gpt-4o-mini`) valida a segurança antes de despachar diretamente.
   - Caso contrário, executa concorrentemente (`asyncio.gather`) o `security_guardrail` e o `vector_router` (Qdrant `routes_index`).
2. **`route_decision` (Conditional Edge):**
   - Se `is_safe == False` ➔ `security_block` ➔ `END`.
   - Se `intent == "recommend"` ➔ `dispatch_recommend` ➔ `END`.
   - Se `intent in ["support", "assistant"]` ➔ `dispatch_assistant` ➔ `END`.
   - Se `intent in ["billing", "faturamento"]` ➔ `dispatch_billing` ➔ `END`.
   - Caso contrário ➔ `handle_fallback` ➔ `END`.
3. **`dispatch_recommend` / `dispatch_assistant` / `dispatch_billing`:** Publica a tarefa no tópico Kafka correspondente e retorna o `task_id` imediatamente para polling.
4. **`handle_fallback`:** Responde saudações diretamente sem onerar o broker de mensageria.

---

## 🧪 6. Suíte de Testes Automatizados (Pytest)

A plataforma possui uma suíte completa de testes automatizados estruturada em [`tests/`](./tests):

```
tests/
├── conftest.py                   # Fixtures: SQLite in-memory com StaticPool, TestClient FastAPI e Mocks
├── unit/                         # Testes Unitários isolados
│   ├── test_guardrail.py         # Schemas de segurança, detecção de Prompt Injection e SQLi
│   ├── test_vector_router.py     # Roteamento semântico vetorial no Qdrant, thresholds e protótipos
│   ├── test_llm_judge.py         # Auditoria LLM-as-a-Judge (aprovação PASS e bloqueio FAIL)
│   ├── test_db_models.py         # Modelos SQLAlchemy e imunidade a SQL Injection
│   └── test_kafka_resilience.py  # Retries, exponential backoff e Dead Letter Queue (DLQ)
└── integration/                  # Testes de Integração de Borda
    └── test_api_routes.py        # Endpoints (/orchestrate, /tasks, /tasks/{id}, validação 422)
```

### Como executar a suíte de testes:

```bash
# Executar todos os 17 testes automatizados:
docker exec -e PYTHONPATH=/app:/packages api_gateway pytest -v -c /pytest.ini /tests

# Executar apenas testes unitários:
docker exec -e PYTHONPATH=/app:/packages api_gateway pytest -v /tests/unit

# Executar apenas testes de integração:
docker exec -e PYTHONPATH=/app:/packages api_gateway pytest -v /tests/integration
```

---

## 🚀 7. Como Adicionar um Novo Agente Especialista

Para adicionar um novo agente especialista (ex: `worker-billing` ou `worker-sql`):

1. **Criar o microserviço** em uma nova pasta (ex: `worker-billing/`) com seu `Dockerfile` e `requirements.txt`.
2. **Herdar o consumidor base do `ai_common`:**
   ```python
   from ai_common.kafka.base_consumer import BaseKafkaWorker
   from ai_common import LLMJudge, get_langfuse_handler
   
   class BillingWorker(BaseKafkaWorker):
       def __init__(self):
           super().__init__(
               worker_name="Worker Financeiro e Faturamento",
               bootstrap_servers="kafka:9092",
               topic="billing_tasks",
               group_id="billing_agent_group",
               dlq_topic="billing_tasks_dlq"
           )
   ```
3. **Auditar a resposta com o `LLMJudge`:**
   ```python
   judge = LLMJudge()
   is_valid, final_text = judge.evaluate(
       context=context_data,
       candidate_response=generated_text,
       task_id=task_id,
       query=query,
       langfuse_handler=handler
   )
   return final_text
   ```
4. **Adicionar o serviço no `docker-compose.yml`** escutando o novo tópico Kafka.
5. **Cadastrar protótipos de intenção** em [`packages/ai_common/qdrant/routes.py`](file:///c:/Users/erik.henning/dev/engineering_ai/packages/ai_common/qdrant/routes.py) para o novo tópico e mapear a rota no `orchestrator.py`.
6. **Adicionar testes unitários correspondentes em `tests/unit/`.**
