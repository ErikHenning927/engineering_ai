import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "127.0.0.1:9092")
PRODUCT_TOPIC = "product_tasks"
PRODUCT_DLQ_TOPIC = "product_tasks_dlq"
ASSISTANT_TOPIC = "assistant_tasks"
ASSISTANT_DLQ_TOPIC = "assistant_tasks_dlq"
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+psycopg2://ai_user:ai_password@127.0.0.1:5432/ai_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LITELLM_URL = os.getenv("LITELLM_URL", "http://litellm_proxy:4000")

