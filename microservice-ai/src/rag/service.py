import logging
import uuid
from typing import List, Dict, Any, Optional
from src.config import settings
from src.rag.embeddings import get_embedding, get_embeddings_batch
from src.rag.qdrant_client import get_qdrant_client, init_products_collection
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue, MatchAny
from openai import OpenAI

# Importações dos módulos modularizados
from src.rag.repository import RAGRepository
from src.rag.prompts import build_system_prompt
from src.rag.utils import estimate_completion_cost, extract_json_from_completion

logger = logging.getLogger("microservice-ai.rag.service")

class RAGProductService:
    @staticmethod
    def index_products(
        limit: Optional[int] = None,
        only_finished: bool = True,
        group_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca os produtos da tabela dim_item no DW SQL Server,
        gera os embeddings e insere na coleção do Qdrant.
        """
        # Garante que a coleção está inicializada
        init_products_collection()
        
        q_client = get_qdrant_client()
        collection_name = settings.QDRANT_COLLECTION
        
        indexed_count = 0
        total_prompt_tokens = 0
        
        try:
            # 1. Buscar produtos para indexação usando o Repositório
            rows = RAGRepository.get_items_for_indexing(
                limit=limit,
                only_finished=only_finished,
                group_filter=group_filter
            )
            total_items = len(rows)
            logger.info(f"Retornados {total_items} itens do DW para indexação.")
            
            if total_items == 0:
                return {
                    "success": True,
                    "indexed_count": 0,
                    "message": "Nenhum produto encontrado com os filtros fornecidos.",
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "estimated_cost_usd": 0.0
                    }
                }
                
            # 2. Processar em batches de 100 itens para gerar embeddings e salvar no Qdrant
            batch_size = 100
            for i in range(0, total_items, batch_size):
                batch_rows = rows[i:i + batch_size]
                
                texts_to_embed = []
                points = []
                
                for row in batch_rows:
                    cod_item = row["CodItem"].strip()
                    desc_item = row["DescItem"].strip()
                    marca = (row["Marca"] or "Desconhecido").strip()
                    voltagem = (row["Voltagem"] or "Não possui voltagem").strip()
                    linha = (row["DescLinha"] or "Desconhecido").strip()
                    familia = (row["DescFamiliaComl"] or "Desconhecido").strip()
                    grupo = (row["DescGrupoComercial"] or "Desconhecido").strip()
                    grupo_estoque = (row["DescGrupoEstoque"] or "Desconhecido").strip()
                    
                    # Constrói string estruturada para representação semântica do item
                    doc_content = (
                        f"Código: {cod_item} | Descrição: {desc_item} | "
                        f"Marca: {marca} | Voltagem: {voltagem} | "
                        f"Linha: {linha} | Família Comercial: {familia} | "
                        f"Grupo Comercial: {grupo} | Grupo Estoque: {grupo_estoque}"
                    )
                    texts_to_embed.append(doc_content)
                    
                # Gerar embeddings em lote via OpenAI
                embeddings, usage = get_embeddings_batch(texts_to_embed)
                total_prompt_tokens += usage["total_tokens"]
                
                # Montar pontos do Qdrant
                for row, emb, text in zip(batch_rows, embeddings, texts_to_embed):
                    cod_item = row["CodItem"].strip()
                    
                    # Qdrant necessita de ID único (gerado de forma determinística via UUID5 do código do item)
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_OID, cod_item))
                    
                    payload = {
                        "CodItem": cod_item,
                        "DescItem": row["DescItem"].strip() if row["DescItem"] else "",
                        "Marca": row["Marca"].strip() if row["Marca"] else "Desconhecido",
                        "Voltagem": row["Voltagem"].strip() if row["Voltagem"] else "Não possui voltagem",
                        "DescGrupoComercial": row["DescGrupoComercial"].strip() if row["DescGrupoComercial"] else "Desconhecido",
                        "DescFamiliaComl": row["DescFamiliaComl"].strip() if row["DescFamiliaComl"] else "Desconhecido",
                        "DescLinha": row["DescLinha"].strip() if row["DescLinha"] else "Desconhecido",
                        "ProdutoAcabado": int(row["ProdutoAcabado"]) if row["ProdutoAcabado"] is not None else 0,
                        "ForaLinha": int(row["ForaLinha"]) if row["ForaLinha"] is not None else 0,
                        "document_content": text
                    }
                    
                    points.append(
                        PointStruct(
                            id=point_id,
                            vector=emb,
                            payload=payload
                        )
                    )
                
                # Upsert no Qdrant
                q_client.upsert(
                    collection_name=collection_name,
                    points=points
                )
                indexed_count += len(points)
                logger.info(f"Indexados {indexed_count}/{total_items} itens...")
                
            return {
                "success": True,
                "indexed_count": indexed_count,
                "message": f"Indexação concluída com sucesso! {indexed_count} itens processados.",
                "usage": {
                    "prompt_tokens": total_prompt_tokens,
                    "completion_tokens": 0,
                    "total_tokens": total_prompt_tokens,
                    "estimated_cost_usd": round(total_prompt_tokens * 0.02 / 1_000_000, 8)
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na indexação de produtos RAG: {e}")
            raise e

    @staticmethod
    def recommend_similar_products(
        query_or_code: str,
        limit: int = 5,
        match_voltage: bool = True,
        match_group: bool = True,
        exclude_self: bool = True
    ) -> Dict[str, Any]:
        """
        Retorna a lista de itens similares usando busca vetorial no Qdrant.
        Se query_or_code for um código existente no DW, busca os detalhes
        deste item para usar como âncora/query vetorial e filtrar compatibilidades.
        """
        q_client = get_qdrant_client()
        
        source_item = None
        original_code = None
        filter_conditions = []
        
        # 1. Verificar se é um código de produto buscando no DW via Repositório
        source_item = RAGRepository.get_source_item_details(query_or_code)
        
        if source_item:
            original_code = source_item["CodItem"].strip()
            desc_item = source_item["DescItem"].strip()
            marca = (source_item["Marca"] or "Desconhecido").strip()
            voltagem = (source_item["Voltagem"] or "Não possui voltagem").strip()
            linha = (source_item["DescLinha"] or "Desconhecido").strip()
            familia = (source_item["DescFamiliaComl"] or "Desconhecido").strip()
            grupo = (source_item["DescGrupoComercial"] or "Desconhecido").strip()
            grupo_estoque = (source_item["DescGrupoEstoque"] or "Desconhecido").strip()
            
            # Constrói o texto âncora do produto original
            search_text = (
                f"Código: {original_code} | Descrição: {desc_item} | "
                f"Marca: {marca} | Voltagem: {voltagem} | "
                f"Linha: {linha} | Família Comercial: {familia} | "
                f"Grupo Comercial: {grupo} | Grupo Estoque: {grupo_estoque}"
            )
            
            # Filtro de voltagem compatível
            if match_voltage and voltagem != "Não possui voltagem":
                volt_lower = voltagem.lower()
                if "110" in volt_lower or "127" in volt_lower:
                    compat_volts = ["110v", "127v", "110v / 220v", "127v / 220v", "bivolt", "Não possui voltagem"]
                elif "220" in volt_lower:
                    compat_volts = ["220v", "110v / 220v", "127v / 220v", "bivolt", "Não possui voltagem"]
                else:
                    compat_volts = [voltagem, "bivolt", "Não possui voltagem"]
                    
                filter_conditions.append(FieldCondition(key="Voltagem", match=MatchAny(any=compat_volts)))
                
            # Filtro de Grupo Comercial
            if match_group and grupo != "Desconhecido":
                filter_conditions.append(FieldCondition(key="DescGrupoComercial", match=MatchValue(value=grupo)))
        else:
            # Caso não encontre o código do item, faz a busca direta por texto em linguagem natural
            search_text = query_or_code
            
        # 2. Gerar embedding do texto de busca
        query_vector, usage = get_embedding(search_text)
        
        # 3. Configurar filtros do Qdrant
        qdrant_filter = None
        must_not_conditions = []
        if original_code and exclude_self:
            must_not_conditions.append(FieldCondition(key="CodItem", match=MatchValue(value=original_code)))
            
        if filter_conditions or must_not_conditions:
            # Removemos a condição de igualdade direta do must se adicionada
            clean_filter_conditions = [c for c in filter_conditions if not (c.key == "CodItem" and isinstance(c.match, MatchValue) and c.match.value == original_code)]
            qdrant_filter = Filter(
                must=clean_filter_conditions,
                must_not=must_not_conditions
            )
            
        # 4. Executar busca no Qdrant
        try:
            search_res = q_client.query_points(
                collection_name=settings.QDRANT_COLLECTION,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=limit
            )
            
            results = []
            for point in search_res.points:
                results.append({
                    "id": point.id,
                    "score": round(point.score, 4),
                    "CodItem": point.payload.get("CodItem"),
                    "DescItem": point.payload.get("DescItem"),
                    "Marca": point.payload.get("Marca"),
                    "Voltagem": point.payload.get("Voltagem"),
                    "DescGrupoComercial": point.payload.get("DescGrupoComercial"),
                    "DescFamiliaComl": point.payload.get("DescFamiliaComl"),
                    "DescLinha": point.payload.get("DescLinha"),
                    "document_content": point.payload.get("document_content")
                })
            return {
                "recommendations": results,
                "usage": usage
            }
        except Exception as e:
            logger.error(f"Erro ao buscar no Qdrant: {e}")
            raise e

    @staticmethod
    def generate_rag_response(
        query_prompt: str,
        limit: int = 5,
        temperature: float = 0.2,
        response_tone: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        response_format: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Processa a pergunta do usuário, busca produtos similares no RAG (Qdrant)
        e gera uma resposta recomendada usando a LLM OpenAI.
        """
        # Tenta extrair possíveis códigos de produtos (letras e números, de 5 a 12 caracteres)
        import re
        tokens = re.findall(r'\b[A-Za-z0-9-]{5,12}\b', query_prompt)
        
        search_key = query_prompt
        source_item = None
        if tokens:
            valid_codes = RAGRepository.validate_codes_exist(tokens)
            if valid_codes:
                search_key = valid_codes[0]
                logger.info(f"Código válido detectado no banco de dados: {search_key}")
                source_item = RAGRepository.get_source_item_details(search_key)
            
        similar_res = RAGProductService.recommend_similar_products(
            query_or_code=search_key,
            limit=limit,
            match_voltage=True,
            match_group=True
        )
        similar_products = similar_res["recommendations"]
        
        # Constrói o contexto em formato legível para o prompt
        if similar_products:
            contexts_str = "\n\n".join([
                f"--- CANDIDATO A TROCA {idx+1} (Similaridade: {p['score']:.2%}) ---\n"
                f"- Código do Item: {p['CodItem']}\n"
                f"- Descrição: {p['DescItem']}\n"
                f"- Marca: {p['Marca']}\n"
                f"- Voltagem: {p['Voltagem']}\n"
                f"- Grupo Comercial: {p['DescGrupoComercial']}\n"
                f"- Família Comercial: {p['DescFamiliaComl']}\n"
                f"- Linha: {p['DescLinha']}"
                for idx, p in enumerate(similar_products)
            ])
        else:
            contexts_str = "(Nenhum produto alternativo correspondente foi encontrado no banco vetorial de contexto.)"
            
        # Constrói o prompt do sistema usando a biblioteca modular de prompts
        system_prompt = build_system_prompt(
            contexts_str=contexts_str,
            source_item=source_item,
            response_tone=response_tone
        )
        
        # Adiciona personalizações adicionais do prompt se existirem
        if custom_prompt:
            system_prompt += f"\nINSTRUÇÕES ADICIONAIS DO USUÁRIO:\n- {custom_prompt}\n"
            
        # Adiciona formatação especial
        if response_format == "table":
            system_prompt += "\nPor favor, apresente a resposta em formato de Tabela Markdown contendo as colunas Código, Descrição, Voltagem e Score de Similaridade.\n"
        elif response_format == "list":
            system_prompt += "\nPor favor, apresente a resposta em tópicos formatados de Lista contendo o Código e Descrição de cada alternativa.\n"
            
        # Sempre exige o JSON estruturado acoplado na resposta
        system_prompt += """
IMPORTANTE: Independentemente do formato textual acima, você DEVE retornar obrigatoriamente no final da sua resposta uma seção com dados estruturados no formato JSON contendo a chave "type" = "recommendations" e a lista de itens sob a chave "items". Siga rigidamente a estrutura abaixo de exemplo:
```json
{
  "type": "recommendations",
  "items": [
    {
      "code": "CÓDIGO_DO_ITEM",
      "name": "DESCRIÇÃO_DO_ITEM",
      "brand": "MARCA",
      "voltage": "VOLTAGEM",
      "similarity_score": 0.9500
    }
  ]
}
```
Substitua os dados do JSON com os produtos da lista fornecida.
"""

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                for msg in history[-6:]:
                    role = msg.get("role")
                    content = msg.get("content")
                    if role in ["user", "assistant"] and content:
                        clean_content = content.split("```json")[0].strip()
                        messages.append({"role": role, "content": clean_content})
            messages.append({"role": "user", "content": query_prompt})

            response = client.chat.completions.create(
                model=settings.COMPLETION_MODEL,
                messages=messages,
                temperature=temperature
            )
            
            final_answer = response.choices[0].message.content or ""
            
            # Extrair uso de tokens e custo aproximado via Módulo Utilitário
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            estimated_cost = 0.0
            
            if response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens
                estimated_cost = estimate_completion_cost(
                    settings.COMPLETION_MODEL,
                    prompt_tokens,
                    completion_tokens
                )
            
            # Extração de JSON do resultado final via Módulo Utilitário
            chart_data = extract_json_from_completion(final_answer)

            return {
                "query_prompt": query_prompt,
                "answer": final_answer,
                "sql_query": None,
                "chart_data": chart_data,
                "retrieved_contexts": [
                    {
                        "table_name": "dim_item",
                        "category": "commercial",
                        "document_content": p["document_content"],
                        "metadata": {
                            "CodItem": p["CodItem"],
                            "Marca": p["Marca"],
                            "Voltagem": p["Voltagem"],
                            "DescGrupoComercial": p["DescGrupoComercial"]
                        },
                        "similarity_score": p["score"]
                    }
                    for p in similar_products
                ],
                "model_used": settings.COMPLETION_MODEL,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "estimated_cost_usd": estimated_cost
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta LLM no RAG de Recomendação: {e}")
            raise e
