import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "127.0.0.1:9092")
PRODUCT_TOPIC = "product_tasks"
PRODUCT_DLQ_TOPIC = os.getenv("PRODUCT_DLQ_TOPIC", "product_tasks_dlq")
GROUP_ID = "product_agent_group"

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "1.0"))

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LITELLM_URL = os.getenv("LITELLM_URL", "http://litellm:4000")

