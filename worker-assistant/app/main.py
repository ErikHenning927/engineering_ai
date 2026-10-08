import logging
from ai_common.kafka.base_consumer import BaseKafkaWorker
from app.core.config import (
    KAFKA_BROKER, 
    ASSISTANT_TOPIC, 
    GROUP_ID, 
    ASSISTANT_DLQ_TOPIC, 
    MAX_RETRIES, 
    RETRY_BASE_DELAY
)
from app.agent.assistant_agent import process_assistant_request, langfuse_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

class AssistantWorker(BaseKafkaWorker):
    def __init__(self):
        super().__init__(
            worker_name="Worker Assistant & Suporte Técnico",
            bootstrap_servers=KAFKA_BROKER,
            topic=ASSISTANT_TOPIC,
            group_id=GROUP_ID,
            dlq_topic=ASSISTANT_DLQ_TOPIC,
            max_retries=MAX_RETRIES,
            retry_base_delay=RETRY_BASE_DELAY,
            langfuse_handler=langfuse_handler
        )

    def process_task(self, query: str, task_data: dict) -> str:
        task_id = task_data.get("task_id", "unknown")
        parameters = task_data.get("parameters", {})
        return process_assistant_request(query, parameters=parameters, task_id=task_id)

if __name__ == "__main__":
    worker = AssistantWorker()
    worker.run()
