from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="AI API Gateway / Orquestrador")

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    # O gateway roda na porta 8001 para não dar conflito com a PoC antiga!
    uvicorn.run(app, host="0.0.0.0", port=8001)
