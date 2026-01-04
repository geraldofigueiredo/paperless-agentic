"""
API Tools for interacting with a Paperless-NGX instance.
All tools are async for better performance and parallel execution.
"""
import os
import logging
import re
import uuid
import unicodedata
import random
import httpx
from dotenv import load_dotenv
from google.adk.tools import ToolContext
from pathlib import Path

from paperless_app.config import TEMP_DATA_DIR, DELETE_AFTER_UPLOAD

# Load environment variables from .env file
load_dotenv()

PAPERLESS_URL = os.getenv("PAPERLESS_URL")
PAPERLESS_API_TOKEN = os.getenv("PAPERLESS_API_TOKEN")

if not PAPERLESS_URL or not PAPERLESS_API_TOKEN:
    raise ValueError(
        "PAPERLESS_URL and PAPERLESS_API_TOKEN must be set in the .env file."
    )

logger = logging.getLogger(__name__)

def _get_auth_headers():
    """Returns the authorization headers for Paperless API requests."""
    return {"Authorization": f"Token {PAPERLESS_API_TOKEN}"}


async def post_document(tool_context: ToolContext, filename: str, correspondent_id: int = None, document_type_id: int = None, tag_ids: list[int] = None, created_date: str = None) -> dict:
    """
    Faz upload de um documento da pasta temp-data para o Paperless-NGX.

    A tool busca automaticamente do state:
    - correspondent_id, tag_ids, document_type_id: IDs criados pelos agents anteriores

    Args:
        filename: Nome do arquivo na pasta temp-data.
        correspondent_id: ID do correspondente (se None, busca do state)
        document_type_id: ID do tipo de documento (se None, busca do state)
        tag_ids: Lista de IDs de tags (se None, busca do state)
        created_date: Data de criação (se None, busca do state)

    Returns:
        dict: {"status": "success/error", "message": "..."}
    """
    endpoint = f"{PAPERLESS_URL}/api/documents/post_document/"

    # Usa o nome do arquivo (sem extensão) como título
    title = Path(filename).stem
    logger.info("Using filename as title: '%s'", title)

    # Fetch missing metadata from state if not provided as arguments
    if correspondent_id is None:
        correspondent_id = tool_context.state.get("correspondent_id")
        if correspondent_id:
            logger.info("Fetched correspondent_id from state: %s", correspondent_id)
            
    if document_type_id is None:
        document_type_id = tool_context.state.get("document_type_id")
        if document_type_id:
            logger.info("Fetched document_type_id from state: %s", document_type_id)
            
    if tag_ids is None:
        tag_ids = tool_context.state.get("tag_ids")
        if tag_ids:
            logger.info("Fetched tag_ids from state: %s", tag_ids)
            
    if created_date is None:
        doc_info = tool_context.state.get("document_info", {})
        created_date = doc_info.get("document_date")
        if created_date:
            logger.info("Fetched created_date from state: %s", created_date)

    data = {
        "title": title,
    }
    if correspondent_id:
        data["correspondent"] = correspondent_id
    if document_type_id:
        data["document_type"] = document_type_id
    if tag_ids:
        data["tags"] = tag_ids
    if created_date:
        # Simple validation: Paperless expects YYYY-MM-DD or ISO 8601
        # Validate if it looks like a date (YYYY-MM-DD) before sending to avoid 400 errors
        if isinstance(created_date, str) and re.match(r"^\d{4}-\d{2}-\d{2}", created_date):
            data["created"] = created_date
            logger.info("Using valid created_date for upload: %s", created_date)
        else:
            logger.warning("Ignoring invalid created_date for upload: %r", created_date)

    try:
        file_path = TEMP_DATA_DIR / filename
        if not file_path.exists():
            error_msg = f"✗ File not found: {filename} in folder {TEMP_DATA_DIR}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

        with open(file_path, "rb") as f:
            file_content = f.read()

        logger.info("✓ Starting upload - file: %s, title: %s", filename, title)

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Generate a unique filename for the upload to avoid conflicts
            original_extension = Path(filename).suffix
            unique_upload_filename = f"{uuid.uuid4()}{original_extension}"
            logger.info(f"Uploading temp file '{filename}' as '{unique_upload_filename}'")

            files = {
                "document": (unique_upload_filename, file_content)
            }

            response = await client.post(
                endpoint,
                headers=_get_auth_headers(),
                data=data,
                files=files,
            )
            response.raise_for_status()

            if DELETE_AFTER_UPLOAD:
                try:
                    os.remove(file_path)
                    logger.info("✓ File '%s' deleted from temp-data.", filename)
                except OSError as e:
                    logger.error("✗ Error deleting file '%s': %s", filename, e)

            result = {"status": "success", "message": "✓ Document uploaded successfully."}
            tool_context.state["upload_result"] = result
            logger.info("✓ Document uploaded successfully from file: %s", filename)
            logger.info("✓ Paperless-NGX response: %s", response.status_code)
            return result
    except httpx.HTTPStatusError as e:
        error_msg = f"✗ HTTP error uploading document: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}
    except httpx.RequestError as e:
        error_msg = f"✗ Request error uploading document: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"✗ Unexpected error uploading document: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}


async def search_documents(tool_context: ToolContext, query: str, tag_ids: list[int] = None, correspondent_id: int = None, document_type_id: int = None) -> list[dict]:
    """
    Searches for documents within the Paperless-NGX system.
    Uses a powerful query language. The user can just say 'receipts from last month'
    and the 'query' parameter should contain that string.

    Args:
        query (str): The main search string. Can be a simple keyword or a complex query like 'correspondent:amazon and added:last-month'.
        tag_ids (list[int], optional): A list of numeric Tag IDs to filter the search by.
        correspondent_id (int, optional): The numeric ID of a correspondent to filter by.
        document_type_id (int, optional): The numeric ID of a document type to filter by.

    Returns:
        list[dict]: A list of document objects matching the search criteria.
    """
    endpoint = f"{PAPERLESS_URL}/api/documents/"
    params = {
        "query": query
    }
    if tag_ids:
        params["tags__id__in"] = ",".join(map(str, tag_ids))
    if correspondent_id:
        params["correspondent__id"] = correspondent_id
    if document_type_id:
        params["document_type__id"] = document_type_id

    logger.info("Searching documents with query: %s", query)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(endpoint, headers=_get_auth_headers(), params=params)
        response.raise_for_status()
        results = response.json().get("results", [])
        logger.info("Found %s documents", len(results))
        tool_context.state["search_results"] = results
        return results


async def list_correspondents() -> list[dict]:
    """
    Retrieves a list of all existing correspondents to get their names and IDs.
    Call this before creating a new correspondent to avoid duplicates.
    """
    endpoint = f"{PAPERLESS_URL}/api/correspondents/"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(endpoint, headers=_get_auth_headers())
        response.raise_for_status()
        return response.json().get("results", [])


async def list_tags() -> list[dict]:
    """
    Retrieves a list of all existing tags to get their names and IDs.
    Call this before creating a new tag to avoid duplicates.
    """
    endpoint = f"{PAPERLESS_URL}/api/tags/"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(endpoint, headers=_get_auth_headers())
        response.raise_for_status()
        return response.json().get("results", [])


async def list_document_types() -> list[dict]:
    """
    Retrieves a list of all existing document types to get their names and IDs.
    """
    endpoint = f"{PAPERLESS_URL}/api/document_types/"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(endpoint, headers=_get_auth_headers())
        response.raise_for_status()
        return response.json().get("results", [])


async def create_correspondent(name: str) -> dict:
    """
    Creates a new correspondent in Paperless-NGX. Use this only after checking
    that the correspondent does not already exist with 'list_correspondents'.

    Args:
        name (str): The name for the new correspondent. Must be unique.

    Returns:
        dict: The newly created correspondent object, including its new ID.
    """
    endpoint = f"{PAPERLESS_URL}/api/correspondents/"
    data = {"name": name}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(endpoint, headers=_get_auth_headers(), json=data)
        response.raise_for_status()
        return response.json()


async def create_document_type(name: str) -> dict:
    """
    Creates a new document type in Paperless-NGX.
    """
    endpoint = f"{PAPERLESS_URL}/api/document_types/"
    data = {"name": name}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(endpoint, headers=_get_auth_headers(), json=data)
        response.raise_for_status()
        return response.json()


async def create_tag(name: str) -> dict:
    """
    Creates a new tag in Paperless-NGX. Handles 400 errors if the tag
    already exists.

    Args:
        name (str): The name for the new tag. Must be unique.

    Returns:
        dict: The newly created tag object, or a message indicating it already exists.
    """
    endpoint = f"{PAPERLESS_URL}/api/tags/"
    random_color = _generate_random_hex_color()
    data = {"name": name, "color": random_color}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, headers=_get_auth_headers(), json=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            logger.warning(
                f"Could not create tag '{name}', it likely already exists. "
                f"API response: {e.response.text}"
            )
            # Return a structure that doesn't break the flow
            return {"status": "already_exists", "name": name}
        else:
            raise e

def _generate_random_hex_color():
    """
    Generates a random hexadecimal color code (e.g., #RRGGBB).
    """
    return '#%06x' % random.randint(0, 0xFFFFFF)


def _normalize_name(name: str) -> str:
    """
    Normaliza um nome para comparação, removendo acentos, espaços extras e convertendo para minúsculas.
    
    Args:
        name: Nome a ser normalizado.
    
    Returns:
        Nome normalizado para comparação.
    """
    if not name:
        return ""
    
    # Remove acentos
    nfd = unicodedata.normalize('NFD', name)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    
    # Converte para minúsculas
    normalized = without_accents.lower()
    
    # Remove espaços extras e caracteres especiais comuns
    normalized = re.sub(r'\s+', ' ', normalized)  # Múltiplos espaços -> um espaço
    normalized = normalized.strip()
    
    # Remove palavras comuns que podem variar
    # (opcional - pode ser expandido conforme necessário)
    normalized = re.sub(r'\b(ltda|ltda\.|ltd|inc|inc\.|corp|corp\.|company|co\.)\b', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized


def _names_are_similar(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """
    Verifica se dois nomes são similares usando normalização e comparação simples.
    
    Args:
        name1: Primeiro nome.
        name2: Segundo nome.
        threshold: Limiar de similaridade (0-1). Padrão: 0.85.
    
    Returns:
        True se os nomes são considerados similares.
    """
    norm1 = _normalize_name(name1)
    norm2 = _normalize_name(name2)
    
    # Comparação exata após normalização
    if norm1 == norm2:
        return True
    
    # Verifica se um nome contém o outro (para casos como "Amazon" vs "Amazon Serviços")
    if norm1 in norm2 or norm2 in norm1:
        # Calcula similaridade simples baseada em palavras comuns
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        # Remove palavras muito curtas (artigos, preposições)
        words1 = {w for w in words1 if len(w) > 2}
        words2 = {w for w in words2 if len(w) > 2}
        
        if len(words1) == 0 or len(words2) == 0:
            return norm1 == norm2
        
        # Calcula similaridade de Jaccard
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if len(union) == 0:
            return False
        
        similarity = len(intersection) / len(union)
        return similarity >= threshold
    
    return False


async def get_or_create_correspondent(tool_context: ToolContext, name: str) -> dict:
    """
    Finds a correspondent by name, performing a smart case-insensitive and normalized search.
    If no similar correspondent is found, a new one is created.
    Always returns a single correspondent object with its ID.

    Args:
        tool_context: The ADK tool context.
        name (str): The name of the correspondent to find or create.

    Returns:
        dict: The correspondent object, including its ID.
    """
    logger.info("Getting or creating correspondent: '%s'", name)
    all_correspondents = await list_correspondents()
    
    # Primeiro tenta match exato (case-insensitive)
    for corr in all_correspondents:
        corr_name = corr.get("name", "")
        if corr_name.lower() == name.lower():
            logger.info("Found exact match correspondent with ID: %s", corr["id"])
            tool_context.state["correspondent_id"] = corr["id"]
            return corr
    
    # Se não encontrou match exato, tenta match similar
    for corr in all_correspondents:
        corr_name = corr.get("name", "")
        if _names_are_similar(name, corr_name):
            logger.info(
                "Found similar correspondent '%s' (requested: '%s') with ID: %s",
                corr_name,
                name,
                corr["id"],
            )
            tool_context.state["correspondent_id"] = corr["id"]
            return corr

    logger.info("Correspondent '%s' not found. Creating a new one.", name)
    new_correspondent = await create_correspondent(name)
    tool_context.state["correspondent_id"] = new_correspondent["id"]
    return new_correspondent


async def get_or_create_tag(tool_context: ToolContext, name: str) -> dict:
    """
    Finds a tag by name, performing a case-insensitive search.
    If no tag is found, a new one is created.
    Always returns a single tag object with its ID.

    Args:
        tool_context: The ADK tool context.
        name (str): The name of the tag to find or create.

    Returns:
        dict: The tag object, including its ID.
    """
    logger.info("Getting or creating tag: '%s'", name)
    all_tags = await list_tags()
    for tag in all_tags:
        if tag.get("name", "").lower() == name.lower():
            logger.info("Found existing tag with ID: %s", tag["id"])
            if "tag_ids" not in tool_context.state:
                tool_context.state["tag_ids"] = []
            if tag["id"] not in tool_context.state["tag_ids"]:
                tool_context.state["tag_ids"].append(tag["id"])
            return tag

    logger.info("Tag '%s' not found. Creating a new one.", name)
    new_tag = await create_tag(name)

    if "tag_ids" not in tool_context.state:
        tool_context.state["tag_ids"] = []
    if new_tag and new_tag.get("id") and new_tag.get("id") not in tool_context.state.get("tag_ids", []):
        tool_context.state["tag_ids"].append(new_tag["id"])
        
    return new_tag


async def select_document_type(tool_context: ToolContext, document_type_id: int) -> str:
    """
    Saves the selected document type ID to the session state.
    Use this after listing document types to persist the selection.
    """
    tool_context.state["document_type_id"] = document_type_id
    logger.info("Selected document_type_id saved to state: %s", document_type_id)
    return f"Document type ID {document_type_id} successfully saved to state."


async def get_or_create_document_type(tool_context: ToolContext, name: str) -> dict:
    """
    Finds a document type by name, performing a smart case-insensitive and normalized search.
    If no similar document type is found, a new one is created.
    Always returns a single document type object with its ID.

    Args:
        tool_context: The ADK tool context.
        name (str): The name of the document type to find or create.

    Returns:
        dict: The document type object, including its ID.
    """
    logger.info("Getting or creating document type: '%s'", name)
    all_types = await list_document_types()
    
    # Primeiro tenta match exato (case-insensitive)
    for dt in all_types:
        dt_name = dt.get("name", "")
        if dt_name.lower() == name.lower():
            logger.info("Found exact match document type with ID: %s", dt["id"])
            tool_context.state["document_type_id"] = dt["id"]
            return dt
    
    # Se não encontrou match exato, tenta match similar
    for dt in all_types:
        dt_name = dt.get("name", "")
        if _names_are_similar(name, dt_name):
            logger.info(
                "Found similar document type '%s' (requested: '%s') with ID: %s",
                dt_name,
                name,
                dt["id"],
            )
            tool_context.state["document_type_id"] = dt["id"]
            return dt

    logger.info("Document type '%s' not found. Creating a new one.", name)
    new_dt = await create_document_type(name)
    tool_context.state["document_type_id"] = new_dt["id"]
    return new_dt

