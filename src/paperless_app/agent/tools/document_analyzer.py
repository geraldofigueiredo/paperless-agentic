"""
Helper tools for document analysis and file management.
The actual document analysis is done by the agent using its native vision capabilities.
"""
import logging

logger = logging.getLogger(__name__)

async def save_document_info(
    tool_context,
    correspondent_name: str,
    document_date: str = None,
    document_type: str = None,
    title: str = None,
    keywords: list = None,
    needs_additional_info: bool = False,
) -> dict:
    """
    Salva as informações extraídas do documento no state do agente.
    
    Esta tool é chamada pelo agente após ele analisar o documento usando suas
    capacidades de visão nativas. O agente extrai as informações e então usa
    esta tool para salvar no state para uso pelos próximos agentes.
    
    Args:
        tool_context: The ADK tool context.
        correspondent_name: Nome do remetente/empresa.
        document_date: Data do documento no formato YYYY-MM-DD.
        document_type: Tipo de documento em português brasileiro.
        title: Título descritivo para o documento.
        keywords: Lista de palavras-chave para categorização.
        needs_additional_info: Se o documento precisa de mais contexto.
    
    Returns:
        dict: Status da operação.
    """
    try:
        # Prepara o dicionário com as informações
        document_info = {
            "status": "success",
            "correspondent_name": correspondent_name or "Desconhecido",
            "document_date": document_date,
            "document_type": document_type or "documento",
            "title": title or "Documento sem título",
            "keywords": keywords or [],
            "needs_additional_info": needs_additional_info,
        }
        
        # Salva no state
        tool_context.state["document_info"] = document_info
        
        logger.info("✓ Document info saved to state: %s", document_info["title"])
        logger.info("  Correspondent: %s", document_info["correspondent_name"])
        logger.info("  Type: %s", document_info["document_type"])
        logger.info("  Keywords: %s", document_info["keywords"])
        
        # Return a simple success message to signal completion to the agent
        return "✓ Informações do documento salvas com sucesso."
    except Exception as e:
        error_msg = f"✗ Error saving document info: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Erro ao salvar informações: {str(e)}"
