import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "127.0.0.1:9092")
PRODUCT_TOPIC = "product_tasks"
