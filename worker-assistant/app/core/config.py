import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "127.0.0.1:9092")
ASSISTANT_TOPIC = os.getenv("ASSISTANT_TOPIC", "assistant_tasks")
ASSISTANT_DLQ_TOPIC = os.getenv("ASSISTANT_DLQ_TOPIC", "assistant_tasks_dlq")
GROUP_ID = os.getenv("GROUP_ID", "assistant_agent_group")

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "1.0"))

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LITELLM_URL = os.getenv("LITELLM_URL", "http://litellm:4000")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+psycopg2://ai_user:ai_password@127.0.0.1:5432/ai_db")
