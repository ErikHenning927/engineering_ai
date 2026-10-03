from typing import Dict, Any, Optional

BASE_PROMPT = """Você é o Products AI, um assistente especialista em trocas de produtos no e-commerce.
Sua principal função é sugerir alternativas válidas de produtos equivalentes para trocas (por garantia, indisponibilidade de estoque ou avaria).
"""

DIRETRIZES_ANTI_ERRO = """DIRETRIZES DE RECOMENDAÇÃO E DE PRODUTOS COMPATÍVEIS (ANTI-ERRO):
1. Use estritamente as especificações dos candidatos de troca apresentados no CONTEXTO abaixo.
2. Certifique-se de que a voltagem seja compatível com a necessidade do cliente (não recomende 220V para quem precisa de 110V/127V).
3. Escreva uma resposta estruturada, explaining porque as opções fornecidas são adequadas.
4. Responda em Português do Brasil de forma concisa, direta e útil.
5. CASO O CONTEXTO ABAIXO ESTEJA VAZIO OU NÃO APRESENTE CANDIDATOS VÁLIDOS, responda claramente informando que não foram encontrados produtos similares elegíveis para troca no momento. NUNCA invente ou crie candidatos fictícios ou com dados que não estejam expressamente descritos no contexto.
"""

TONE_INSTRUCTIONS = {
    "formal": "Adote um tom formal, profissional e analítico nas explicações.",
    "descontraido": "Adote um tom amigável, leve e compreensível, ideal para falar diretamente com o cliente.",
    "direto": "Adote um tom direto, conciso, focado estritamente nas especificações e código do produto.",
    "didatico": "Adote um tom didático e explicativo, facilitando o entendimento de cada característica técnica."
}

def format_source_product_context(source_item: Optional[Dict[str, Any]]) -> str:
    if not source_item:
        return ""
    return (
        f"PRODUTO DE ORIGEM (SOLICITAÇÃO DE TROCA COM DEFEITO):\n"
        f"- Código do Item: {source_item.get('CodItem', '').strip()}\n"
        f"- Descrição: {source_item.get('DescItem', '').strip() if source_item.get('DescItem') else 'Desconhecido'}\n"
        f"- Marca: {source_item.get('Marca', '').strip() if source_item.get('Marca') else 'Desconhecido'}\n"
        f"- Voltagem: {source_item.get('Voltagem', '').strip() if source_item.get('Voltagem') else 'Não possui voltagem'}\n"
        f"- Grupo Comercial: {source_item.get('DescGrupoComercial', '').strip() if source_item.get('DescGrupoComercial') else 'Desconhecido'}\n"
        f"- Família Comercial: {source_item.get('DescFamiliaComl', '').strip() if source_item.get('DescFamiliaComl') else 'Desconhecido'}\n"
        f"- Linha: {source_item.get('DescLinha', '').strip() if source_item.get('DescLinha') else 'Desconhecido'}\n"
    )

def build_system_prompt(
    contexts_str: str,
    source_item: Optional[Dict[str, Any]] = None,
    response_tone: Optional[str] = None
) -> str:
    source_product_str = format_source_product_context(source_item)
    
    prompt = f"""{BASE_PROMPT}

{DIRETRIZES_ANTI_ERRO}
"""
    if response_tone:
        tone_msg = TONE_INSTRUCTIONS.get(response_tone.lower(), response_tone)
        prompt += f"\nDIRETRIZE DE TOM DE VOZ:\n- {tone_msg}\n"
        
    if source_product_str:
        prompt += f"\n{source_product_str}\n"
        
    prompt += f"CONTEXTO DE PRODUTOS SIMILARES ENCONTRADOS (RAG):\n{contexts_str}\n"
    return prompt
