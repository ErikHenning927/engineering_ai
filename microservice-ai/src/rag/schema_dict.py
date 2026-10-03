"""
Dicionário de Conhecimento Semântico de Negócio (Trocas).
Este arquivo contém a descrição dos produtos pelo RAG.
A estrutura física de colunas é descoberta e indexada dinamicamente do banco SQLSERVER.

"""

PRODUCTS_SCHEMA_KNOWLEDGE = [
    {
        "table_name": "system_architecture_master",
        "category": "system_overview",
        "business_description": """
        Sistema para busca de similiaridade de produtos para troca e comunicação com o usuário final. 
        """,
        "metadata": {
            "entity": "SystemMasterOverview",
            "scope": "enterprise_ecommerce_control_tower"
        }
    },
    {
        "table_name": "dim_item",
        "category": "commercial",
        "business_description": "Registrar todas as informações dos itens, familia, linha, grupo de estoque e detalhes.",
        "metadata": {
            "entity": "OrderHeader",
            "joins": [""],
            "primary_key": "id"
        }
    }
]

ECOMMERCE_SCHEMA_KNOWLEDGE = PRODUCTS_SCHEMA_KNOWLEDGE
