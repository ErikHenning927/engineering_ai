import json
from confluent_kafka import Consumer, KafkaError
from app.core.config import KAFKA_BROKER, PRODUCT_TOPIC, GROUP_ID
from app.agent.product_agent import process_recommendation
from app.db.postgres_client import save_result

consumer_config = {
    'bootstrap.servers': KAFKA_BROKER,
    'group.id': GROUP_ID,
    'auto.offset.reset': 'earliest',
    'broker.address.family': 'v4'
}

consumer = Consumer(consumer_config)
consumer.subscribe([PRODUCT_TOPIC])

print("=======================================")
print(" Worker Recomendador Iniciado")
print(" Escutando a fila Kafka...")
print("=======================================")

try:
    while True:
        msg = consumer.poll(1.0)
        
        if msg is None:
            continue
        if msg.error():
            err_code = msg.error().code()
            if err_code == KafkaError._PARTITION_EOF:
                continue
            elif err_code == KafkaError.UNKNOWN_TOPIC_OR_PART:
                # O tópico ainda não foi criado pelo Gateway, vamos esperar
                continue
            else:
                print(msg.error())
                break
                
        # Deserializa o evento Kafka
        try:
            task_data = json.loads(msg.value().decode('utf-8'))
            task_id = task_data.get('task_id')
            query = task_data.get('query')
            
            print(f"\n🚀 [Nova Tarefa] ID: {task_id}")
            
            # Chama o Agente Especialista
            answer = process_recommendation(query, task_id=task_id)
            
            print(f"✅ [Tarefa Concluída] Resultado:\n{answer}")
            
            # Salva no PostgreSQL
            save_result(task_id, query, answer)
            print("💾 Resultado salvo no banco de dados!")
            
        except Exception as e:
            print(f"Ignorando mensagem inválida: {msg.value()} Erro: {e}")
        
except KeyboardInterrupt:
    pass
finally:
    consumer.close()
