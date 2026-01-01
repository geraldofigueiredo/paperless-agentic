"""
Agent definitions for the Paperless Orchestrator system using the Google ADK.

This file defines a multi-agent architecture with specialized sub-agents.

"""
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import FunctionTool, load_artifacts
from google.adk.tools.tool_context import ToolContext
from dotenv import load_dotenv
import logging
import base64
from typing import Optional
from google.genai import types
from pathlib import Path

from . import prompts
from .tools import paperless_api, document_analyzer, file_manager
from .config import TEMP_DATA_DIR

MODEL = "gemini-2.0-flash"
logger = logging.getLogger(__name__)

async def save_pdf_to_temp_and_create_artifact(
    tool_context: ToolContext, file_content: str, file_name: str
) -> str:
    """
    Saves a PDF file to the temp-data directory and creates an artifact.

    Args:
        tool_context: The context of the tool.
        file_content: The base64-encoded content of the PDF file.
        file_name: The name of the file.

    Returns:
        A success message with the saved artifact's name.
    """
    try:
        file_bytes = base64.b64decode(file_content)
    except Exception as e:
        logger.error(f"Failed to decode base64 content for file '{file_name}': {e}")
        return f"Error: Invalid file content."

    # Save file to temp-data
    file_path = TEMP_DATA_DIR / file_name
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    logger.info(f"File '{file_name}' saved to '{TEMP_DATA_DIR}'.")

    # Save filename to state
    tool_context.state["filename"] = file_name

    # Create artifact
    artifact_part = types.Part(
        inline_data=types.Blob(mime_type="application/pdf", data=file_bytes)
    )
    await tool_context.save_artifact(file_name, artifact_part)
    
    return f"Artifact {file_name} saved successfully."

# Document Analyzer Agent
document_analyzer_agent = Agent(
    name="document_analyzer_agent",
    model=MODEL,
    description="Analisa documentos e extrai metadados usando capacidades de visão nativas",
    instruction=prompts.DOCUMENT_ANALYZER_INSTRUCTION,
    tools=[
        load_artifacts,
        FunctionTool(func=document_analyzer.save_document_info),
        FunctionTool(func=file_manager.extract_text_from_pdf),
    ],
    output_key="document_metadata",
)

# Metadata Creator Agent
metadata_creator_agent = Agent(
    name="metadata_creator_agent",
    model=MODEL,
    description="Cria correspondentes e tags necessários no Paperless-NGX",
    instruction=prompts.METADATA_CREATOR_INSTRUCTION,
    tools=[
        FunctionTool(func=paperless_api.get_or_create_correspondent),
        FunctionTool(func=paperless_api.get_or_create_tag),
        FunctionTool(func=paperless_api.list_document_types),
    ],
    output_key="metadata_ids",
)

# Document Uploader Agent
document_uploader_agent = Agent(
    name="document_uploader_agent",
    model=MODEL,
    description="Faz upload do documento com todos os metadados coletados",
    instruction=prompts.DOCUMENT_UPLOADER_INSTRUCTION,
    tools=[
        load_artifacts,
        FunctionTool(func=paperless_api.post_document),
    ],
    output_key="upload_result",
)

# Ingestion Workflow Agent (Sequential)
ingestion_workflow_agent = SequentialAgent(
    name="ingestion_workflow_agent",
    description="Fluxo completo de cadastro de documentos: análise → metadados → upload",
    sub_agents=[
        document_analyzer_agent,
        metadata_creator_agent,
        document_uploader_agent,
    ],
)

# Search Agent
search_agent = Agent(
    name="search_agent",
    model=MODEL,
    description="Busca documentos no Paperless-NGX usando linguagem natural",
    instruction=prompts.SEARCH_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(func=paperless_api.search_documents),
        FunctionTool(func=paperless_api.list_document_types),
    ],
)

# Root Agent
root_agent = Agent(
    name="paperless_root_agent",
    model=MODEL,
    description="Assistente principal para gerenciar documentos no Paperless-NGX",
    instruction=prompts.ROOT_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(func=save_pdf_to_temp_and_create_artifact),
        load_artifacts,
    ],
    sub_agents=[
        ingestion_workflow_agent,
        search_agent,
    ],
)
