import json
import time
import signal
import logging
from typing import Optional, Callable
from confluent_kafka import Consumer, KafkaError
from .dlq_producer import DLQProducer
from ..db.session import save_task_result

logger = logging.getLogger("ai_common.worker")

class BaseKafkaWorker:
    """
    Classe base para Workers Especialistas.
    Gerencia:
      - Loop de consumo Kafka com commit seguro
      - Graceful Shutdown (SIGINT, SIGTERM)
      - Política de Retries com Exponential Backoff
      - Roteamento automático para Dead Letter Queue (DLQ)
      - Persistência padronizada no PostgreSQL
    """
    
    def __init__(
        self,
        worker_name: str,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        dlq_topic: str,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        langfuse_handler = None
    ):
        self.worker_name = worker_name
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.dlq_topic = dlq_topic
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.langfuse_handler = langfuse_handler
        
        self.is_running = True
        self.dlq_producer = DLQProducer(bootstrap_servers, default_dlq_topic=dlq_topic)
        
        # Configurar consumer
        self.consumer = Consumer({
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
            'broker.address.family': 'v4',
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000
        })
        self.consumer.subscribe([topic])
        
        # Configurar interceptação de sinais
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        sig_name = signal.Signals(signum).name
        logger.info(f"\n🛑 [{self.worker_name}] Sinal {sig_name} recebido. Iniciando Graceful Shutdown...")
        self.is_running = False

    def process_task(self, query: str, task_data: dict) -> str:
        """Método abstrato que deve ser implementado pelo Worker Especialista."""
        raise NotImplementedError("O Worker especialista deve implementar o método process_task()")

    def run(self):
        """Inicia o loop resiliente do Worker."""
        logger.info("==================================================")
        logger.info(f"🤖 {self.worker_name} Iniciado")
        logger.info(f"📡 Escutando tópico: '{self.topic}' (Grupo: '{self.group_id}')")
        logger.info(f"🔁 Retries: até {self.max_retries} tentativas com Exponential Backoff")
        logger.info(f"🚨 DLQ Topic: '{self.dlq_topic}'")
        logger.info("==================================================")
        
        try:
            while self.is_running:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    err_code = msg.error().code()
                    if err_code == KafkaError._PARTITION_EOF:
                        continue
                    elif err_code == KafkaError.UNKNOWN_TOPIC_OR_PART:
                        continue
                    else:
                        logger.error(f"Erro no Kafka Consumer: {msg.error()}")
                        break

                try:
                    task_data = json.loads(msg.value().decode('utf-8'))
                except Exception as parse_err:
                    logger.error(f"Mensagem corrompida descartada: {msg.value()} | Erro: {parse_err}")
                    continue

                task_id = task_data.get('task_id', 'unknown')
                query = task_data.get('query', '')
                logger.info(f"\n🚀 [{self.worker_name}] Tarefa Recebida | ID: {task_id} | Query: '{query}'")

                # Execução com Retries e Backoff
                success = False
                last_error = None

                for attempt in range(1, self.max_retries + 1):
                    try:
                        logger.info(f"⏳ Executando tarefa {task_id} (Tentativa {attempt}/{self.max_retries})...")
                        answer = self.process_task(query, task_data)
                        
                        logger.info(f"✅ [{self.worker_name}] Tarefa Concluída para {task_id}")
                        save_task_result(task_id, query, answer)
                        success = True
                        break
                    except Exception as e:
                        last_error = e
                        logger.warning(f"⚠️ [Falha na Tentativa {attempt}/{self.max_retries}] Erro na tarefa {task_id}: {e}")
                        if attempt < self.max_retries:
                            backoff = self.retry_base_delay * (2 ** (attempt - 1))
                            logger.info(f"🔁 Aguardando {backoff:.1f}s antes do próximo retry...")
                            time.sleep(backoff)

                if not success:
                    logger.error(f"❌ Tarefa {task_id} falhou após {self.max_retries} tentativas. Enviando para DLQ...")
                    self.dlq_producer.send(task_data, last_error, retries_attempted=self.max_retries)

        except Exception as fatal_err:
            logger.error(f"Erro fatal no loop do {self.worker_name}: {fatal_err}")

        finally:
            self._cleanup()

    def _cleanup(self):
        logger.info(f"🧹 Encerrando conexões de {self.worker_name}...")
        try:
            try:
                self.consumer.commit(asynchronous=False)
            except KafkaError as ke:
                if ke.code() != KafkaError._NO_OFFSET:
                    logger.warning(f"Aviso ao comitar offsets: {ke}")
            except Exception:
                pass
            self.consumer.close()
            logger.info("🔒 Consumidor Kafka fechado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao fechar consumidor: {e}")

        try:
            self.dlq_producer.flush()
            logger.info("📤 Fila de DLQ sincronizada.")
        except Exception as e:
            logger.error(f"Erro ao descarregar DLQ: {e}")

        if self.langfuse_handler:
            try:
                self.langfuse_handler.flush()
                logger.info("🔭 Telemetria Langfuse finalizada.")
            except Exception as e:
                logger.error(f"Erro ao descarregar Langfuse: {e}")

        logger.info(f"👋 {self.worker_name} finalizado com sucesso.")
