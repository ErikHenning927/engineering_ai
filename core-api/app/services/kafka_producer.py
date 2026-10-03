import json
from confluent_kafka import Producer
from app.core.config import KAFKA_BROKER

producer_config = {
    'bootstrap.servers': KAFKA_BROKER,
    'broker.address.family': 'v4'
}

producer = Producer(producer_config)

def delivery_report(err, msg):
    if err is not None:
        print(f"Erro ao enviar evento Kafka: {err}")
    else:
        print(f"Evento enfileirado no tópico {msg.topic()}")

def publish_task(topic: str, task_data: dict):
    producer.produce(
        topic, 
        value=json.dumps(task_data).encode('utf-8'), 
        callback=delivery_report
    )
    producer.flush() # Garante o envio imediato da mensagem
