import logging
import pymssql
from src.config import settings

logger = logging.getLogger("microservice-ai.database")

def get_dw_connection():
    """Conecta ao SQL Server do DW usando as credenciais da .env."""
    try:
        conn = pymssql.connect(
            server=settings.DW_HOST,
            port=str(settings.DW_PORT),
            user=settings.DW_USER,
            password=settings.DW_PASSWORD,
            database=settings.DW_NAME,
            timeout=10
        )
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao SQL Server DW: {e}")
        raise e

# Wrapper compatível com código legado/estrutura
def get_db_connection():
    return get_dw_connection()

def init_db():
    """Valida a conexão com o DW SQL Server no início do microserviço."""
    try:
        conn = get_dw_connection()
        conn.close()
        logger.info("Conexão de teste com o SQL Server DW inicializada com sucesso.")
    except Exception as e:
        logger.warning(f"Não foi possível validar a conexão inicial com o SQL Server DW: {e}")
