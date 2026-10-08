import json
import logging
from datetime import datetime
from typing import Optional
from confluent_kafka import Producer

logger = logging.getLogger("ai_common.dlq")

class DLQProducer:
    """Produtor reutilizável para Dead Letter Queues."""
    
    def __init__(self, bootstrap_servers: str, default_dlq_topic: str = "tasks_dlq"):
        self.bootstrap_servers = bootstrap_servers
        self.default_dlq_topic = default_dlq_topic
        self._producer = Producer({
            'bootstrap.servers': bootstrap_servers,
            'broker.address.family': 'v4'
        })

    def _delivery_report(self, err, msg):
        if err is not None:
            logger.error(f"❌ [DLQ] Falha ao entregar mensagem no tópico DLQ: {err}")
        else:
            logger.warning(f"⚠️ [DLQ] Mensagem enviada para {msg.topic()} [partição {msg.partition()}]")

    def send(self, task_data: dict, error: Exception, retries_attempted: int, dlq_topic: Optional[str] = None):
        target_topic = dlq_topic or self.default_dlq_topic
        dlq_payload = {
            "task_id": task_data.get("task_id", "unknown"),
            "original_payload": task_data,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "retries_attempted": retries_attempted,
            "failed_at": datetime.utcnow().isoformat() + "Z"
        }
        
        try:
            self._producer.produce(
                target_topic,
                value=json.dumps(dlq_payload).encode('utf-8'),
                callback=self._delivery_report
            )
            self._producer.poll(0)
            logger.warning(f"🚨 [DLQ] Tarefa {dlq_payload['task_id']} despachada para a DLQ '{target_topic}'.")
        except Exception as e:
            logger.error(f"❌ Erro crítico ao enviar para DLQ: {e}")

    def flush(self, timeout: float = 2.0):
        self._producer.flush(timeout)

# Instância padrão / helper
_default_dlq_producer: Optional[DLQProducer] = None

def get_dlq_producer(bootstrap_servers: str, default_dlq_topic: str = "tasks_dlq") -> DLQProducer:
    global _default_dlq_producer
    if _default_dlq_producer is None:
        _default_dlq_producer = DLQProducer(bootstrap_servers, default_dlq_topic)
    return _default_dlq_producer

def send_to_dlq(bootstrap_servers: str, dlq_topic: str, task_data: dict, error: Exception, retries_attempted: int):
    producer = get_dlq_producer(bootstrap_servers, dlq_topic)
    producer.send(task_data, error, retries_attempted, dlq_topic=dlq_topic)
