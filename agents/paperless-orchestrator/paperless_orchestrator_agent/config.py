"""
Configuration for the Paperless Orchestrator agent.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Diretório base do agente
AGENT_DIR = Path(__file__).parent.parent

# Pasta temporária para arquivos a serem processados
# Pode ser configurada via variável de ambiente TEMP_DATA_DIR
# Padrão: temp-data dentro do diretório do agente
TEMP_DATA_DIR = Path(
    os.getenv("TEMP_DATA_DIR", str(AGENT_DIR / "temp-data"))
)

# Garante que o diretório existe
TEMP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Configuração para deletar arquivo após upload bem-sucedido
DELETE_AFTER_UPLOAD = os.getenv("DELETE_AFTER_UPLOAD", "true").lower() == "true"

