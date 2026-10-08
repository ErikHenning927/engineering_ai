import json
import logging
from typing import Optional
from aiokafka import AIOKafkaProducer

logger = logging.getLogger("ai_common.async_kafka")

class AsyncKafkaProducerManager:
    """Gerenciador assíncrono de produtor Kafka com aiokafka."""
    
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> AIOKafkaProducer:
        if self._producer is None:
            logger.info(f"Conectando AIOKafkaProducer ao broker {self.bootstrap_servers}...")
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await self._producer.start()
            logger.info("✅ AIOKafkaProducer conectado e pronto!")
        return self._producer

    async def stop(self):
        if self._producer is not None:
            try:
                logger.info("Encerrando AIOKafkaProducer...")
                await self._producer.stop()
                logger.info("AIOKafkaProducer encerrado com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao encerrar AIOKafkaProducer: {e}")
            finally:
                self._producer = None

    async def publish(self, topic: str, data: dict):
        if self._producer is None:
            await self.start()
        record_metadata = await self._producer.send_and_wait(topic, data)
        logger.info(f"📤 [Kafka Async] Mensagem publicada no tópico '{topic}' (partição {record_metadata.partition}, offset {record_metadata.offset})")
        return record_metadata

# Helper global
_manager: Optional[AsyncKafkaProducerManager] = None

def get_async_producer_manager(bootstrap_servers: str) -> AsyncKafkaProducerManager:
    global _manager
    if _manager is None or _manager.bootstrap_servers != bootstrap_servers:
        _manager = AsyncKafkaProducerManager(bootstrap_servers)
    return _manager

async def init_kafka_producer(bootstrap_servers: str):
    manager = get_async_producer_manager(bootstrap_servers)
    return await manager.start()

async def stop_kafka_producer():
    global _manager
    if _manager is not None:
        await _manager.stop()
        _manager = None

async def publish_task(bootstrap_servers: str, topic: str, task_data: dict):
    manager = get_async_producer_manager(bootstrap_servers)
    return await manager.publish(topic, task_data)
