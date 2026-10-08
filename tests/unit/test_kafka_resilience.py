import pytest
from unittest.mock import MagicMock, patch
from ai_common.kafka.dlq_producer import DLQProducer

def test_dlq_producer_publish_failure():
    """Testa envio de mensagem para a Dead Letter Queue com metadados de erro."""
    with patch("ai_common.kafka.dlq_producer.Producer") as mock_producer_cls:
        mock_instance = MagicMock()
        mock_producer_cls.return_value = mock_instance
        
        dlq = DLQProducer(bootstrap_servers="mock:9092", default_dlq_topic="test_dlq")
        
        original_msg = {"task_id": "task-error-1", "query": "dados com erro"}
        error_details = Exception("Timeout ao contatar LLM após 3 tentativas")
        
        dlq.send(task_data=original_msg, error=error_details, retries_attempted=3)
        dlq.flush(timeout=1.0)
        
        # Verifica se o producer do Confluent Kafka foi acionado com produce, poll e flush
        assert mock_instance.produce.called
        assert mock_instance.poll.called
        assert mock_instance.flush.called
