import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("microservice-ai.rag.utils")

def estimate_completion_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estima o custo do modelo com base no número de tokens utilizados."""
    if "gpt-4o-mini" in model_name:
        input_price = 0.15
        output_price = 0.60
    elif "gpt-4o" in model_name:
        input_price = 5.00
        output_price = 15.00
    elif "gpt-3.5-turbo" in model_name:
        input_price = 0.50
        output_price = 1.50
    else:
        input_price = 0.15
        output_price = 0.60
    
    cost = (prompt_tokens * input_price / 1_000_000) + (completion_tokens * output_price / 1_000_000)
    return round(cost, 6)

def extract_json_from_completion(final_answer: str) -> Optional[Dict[str, Any]]:
    """Extrai e faz o parse de blocos JSON retornados pelo modelo."""
    chart_data = None
    json_str = None
    lower_final_answer = final_answer.lower()
    
    if "```json" in lower_final_answer:
        start_idx = lower_final_answer.find("```json") + 7
        end_idx = lower_final_answer.find("```", start_idx)
        if end_idx != -1:
            json_str = final_answer[start_idx:end_idx].strip()
            
    if json_str:
        try:
            chart_data = json.loads(json_str)
        except Exception as json_err:
            logger.error(f"Erro ao parsear dados estruturados JSON da resposta: {json_err}")
    return chart_data
