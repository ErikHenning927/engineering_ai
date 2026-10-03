from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from src.rag.service import RAGProductService

router = APIRouter(prefix="/rag", tags=["RAG Product Recommendation"])

class SearchContextResponseItem(BaseModel):
    table_name: str
    category: str
    document_content: str
    metadata: Optional[Dict[str, Any]] = None
    similarity_score: float

class IndexProductsRequest(BaseModel):
    limit: Optional[int] = Field(default=10, description="Limite de itens a indexar para fins de testes")
    only_finished: Optional[bool] = Field(default=True, description="Apenas produtos acabados")
    group_filter: Optional[str] = Field(default="VENTILADORES", description="Filtrar por grupo comercial específico (ex: 'VENTILADORES')")

class RecommendProductsRequest(BaseModel):
    query_or_code: str = Field(..., description="Código do item de origem ou termo de busca", example="033101302")
    limit: Optional[int] = Field(default=5, description="Quantidade máxima de recomendações")
    match_voltage: Optional[bool] = Field(default=True, description="Exigir voltagem compatível")
    match_group: Optional[bool] = Field(default=True, description="Exigir mesmo grupo comercial")
    exclude_self: Optional[bool] = Field(default=True, description="Excluir o próprio item de origem das sugestões")

class RecommendProductsResponseItem(BaseModel):
    id: str
    score: float
    CodItem: str
    DescItem: str
    Marca: str
    Voltagem: str
    DescGrupoComercial: str
    DescFamiliaComl: str
    DescLinha: str
    document_content: str

class RecommendProductsResponse(BaseModel):
    recommendations: List[RecommendProductsResponseItem]
    usage: Optional[Dict[str, Any]] = None

class AskRequest(BaseModel):
    query_prompt: str = Field(..., description="Pergunta ou solicitação de recomendação do usuário", example="Recomende uma troca para o item 033101302")
    limit: Optional[int] = Field(default=5, description="Quantidade máxima de contextos a recuperar no RAG")
    temperature: Optional[float] = Field(default=0.2, description="Temperatura da LLM para controlar criatividade")
    response_tone: Optional[str] = Field(default=None, description="Tom de resposta da LLM (formal, descontraido, direto, didatico)")
    custom_prompt: Optional[str] = Field(default=None, description="Prompt ou instruções personalizadas adicionais para o assistente")
    response_format: Optional[str] = Field(default=None, description="Formato desejado da resposta (text, table, list)")
    history: Optional[List[Dict[str, str]]] = Field(default=None, description="Histórico de conversas anterior")

class AskResponse(BaseModel):
    query_prompt: str
    answer: str
    sql_query: Optional[str] = None
    chart_data: Optional[Dict[str, Any]] = None
    retrieved_contexts: List[SearchContextResponseItem]
    model_used: str
    usage: Optional[Dict[str, Any]] = None

@router.post("/index-products")
def index_products(request: Optional[IndexProductsRequest] = None):
    """Busca produtos de dim_item no SQL Server DW, gera embeddings e insere no Qdrant."""
    try:
        req = request or IndexProductsRequest()
        result = RAGProductService.index_products(
            limit=req.limit,
            only_finished=req.only_finished,
            group_filter=req.group_filter
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recommend-products", response_model=RecommendProductsResponse)
def recommend_products(request: RecommendProductsRequest):
    """Busca produtos similares recomendados para troca usando similaridade vetorial e regras de negócio."""
    try:
        result = RAGProductService.recommend_similar_products(
            query_or_code=request.query_or_code,
            limit=request.limit,
            match_voltage=request.match_voltage,
            match_group=request.match_group,
            exclude_self=request.exclude_self
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask", response_model=AskResponse)
def ask_ai(request: AskRequest):
    """Combina busca vetorial de produtos com LLM OpenAI para responder dúvidas e justificar propostas de troca."""
    try:
        result = RAGProductService.generate_rag_response(
            query_prompt=request.query_prompt,
            limit=request.limit,
            temperature=request.temperature if request.temperature is not None else 0.2,
            response_tone=request.response_tone,
            custom_prompt=request.custom_prompt,
            response_format=request.response_format,
            history=request.history
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
