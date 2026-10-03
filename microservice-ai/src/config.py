import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    COMPLETION_MODEL: str = os.getenv("COMPLETION_MODEL", "gpt-4o-mini")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8000,http://localhost:8002")
    
    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: int = int(os.getenv("DB_PORT")) if os.getenv("DB_PORT") else 5432
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "")
    

    #DW Conn
    DW_HOST: str = os.getenv("DW_HOST", "")
    DW_PORT: int = int(os.getenv("DW_PORT")) if os.getenv("DW_PORT") else 1433
    DW_USER: str = os.getenv("DW_USER", "")
    DW_PASSWORD: str = os.getenv("DW_PASSWORD", "")
    DW_NAME: str = os.getenv("DW_NAME", "")
    
    # Qdrant Vector DB
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "products")

    PORT: int = int(os.getenv("PORT", "8002"))

settings = Settings()

