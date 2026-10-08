# 🤖 Engineering AI - Multi-Agent AI Platform

Plataforma corporativa de IA Multi-Agente distribuída e event-driven com Apache Kafka, LangGraph, Qdrant, PostgreSQL, LiteLLM e Langfuse.

---

## 📖 Documentação Completa

Toda a documentação detalhada, guia de arquitetura, migrations, seeds e passo a passo de execução estão disponíveis na pasta [`docs/`](./docs):

- 📘 [**README Completo e Guia de Execução**](./docs/README.md)
- 🏛️ [**Plano Detalhado de Arquitetura e Decisões de Engenharia**](./docs/ARCHITECTURE_PLAN.md)
- 🤖 [**Especificação dos Agentes & Guardrails**](./AGENTS.md)

---

## ⚡ Início Rápido

```bash
# 1. Configurar variáveis de ambiente
cp .env.example .env # preencha com suas chaves de API

# 2. Subir todos os serviços em contêineres Docker
docker compose up -d --build

# 3. Executar o Seed da base relacional e vetorial
docker exec -e PYTHONPATH=/packages worker_recommendation python /packages/ai_common/seed.py
```

### 🌐 Acessos Principais
- **Swagger API Gateway:** [http://localhost:8001/docs](http://localhost:8001/docs)
- **Langfuse LLMOps Dashboard:** [http://localhost:3000](http://localhost:3000)
- **Qdrant Vector Dashboard:** [http://localhost:6333/dashboard](http://localhost:6333/dashboard)
- **LiteLLM Proxy:** [http://localhost:4000](http://localhost:4000)
- **Frontend Demo:** `demo/index.html`
