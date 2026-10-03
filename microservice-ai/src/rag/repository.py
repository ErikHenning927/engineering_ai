import logging
from typing import List, Dict, Any, Optional
from src.database import get_dw_connection

logger = logging.getLogger("microservice-ai.rag.repository")

class RAGRepository:
    @staticmethod
    def get_items_for_indexing(
        limit: Optional[int] = None,
        only_finished: bool = True,
        group_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Busca produtos de dim_item no DW SQL Server."""
        conn = get_dw_connection()
        try:
            select_clause = "SELECT"
            if limit is not None:
                select_clause = f"SELECT TOP {limit}"
                
            query = f"""
                {select_clause} 
                    CodItem, DescItem, Un, DescGrupoEstoque, DescFamiliaComl, 
                    DescFamMaterial, DescGrupoComercial, DescLinha, Marca, 
                    Voltagem, ProdutoAcabado, ForaLinha
                FROM dim_item
                WHERE CodItem IS NOT NULL AND DescItem IS NOT NULL
            """
            
            params = []
            if only_finished:
                query += " AND ProdutoAcabado = 1"
            if group_filter:
                query += " AND DescGrupoComercial = %s"
                params.append(group_filter)
                
            with conn.cursor(as_dict=True) as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
            return rows
        except Exception as e:
            logger.error(f"Erro ao buscar itens para indexação no DW: {e}")
            raise e
        finally:
            conn.close()

    @staticmethod
    def get_source_item_details(cod_item: str) -> Optional[Dict[str, Any]]:
        """Busca detalhes de um produto de origem específico pelo código."""
        conn = get_dw_connection()
        try:
            with conn.cursor(as_dict=True) as cur:
                cur.execute("""
                    SELECT TOP 1
                        CodItem, DescItem, Un, DescGrupoEstoque, DescFamiliaComl, 
                        DescFamMaterial, DescGrupoComercial, DescLinha, Marca, 
                        Voltagem, ProdutoAcabado, ForaLinha
                    FROM dim_item
                    WHERE CodItem = %s
                """, (cod_item.strip(),))
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do item {cod_item} no DW: {e}")
            raise e
        finally:
            conn.close()

    @staticmethod
    def validate_codes_exist(codes: List[str]) -> List[str]:
        """Dada uma lista de possíveis códigos, retorna apenas os existentes no DW."""
        if not codes:
            return []
        conn = get_dw_connection()
        try:
            with conn.cursor(as_dict=True) as cur:
                placeholders = ", ".join(["%s"] * len(codes))
                cur.execute(f"SELECT DISTINCT CodItem FROM dim_item WHERE CodItem IN ({placeholders})", tuple(codes))
                rows = cur.fetchall()
                return [r["CodItem"].strip() for r in rows if r.get("CodItem")]
        except Exception as e:
            logger.error(f"Erro ao validar códigos no DW: {e}")
            return []
        finally:
            conn.close()
