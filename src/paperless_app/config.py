"""
Configuration for the Paperless Orchestrator agent.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# `config.py` is in `src/paperless_app/`, so we go up two levels to get the project root.
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).parent.parent.parent))

# Pasta temporária para arquivos a serem processados
TEMP_DATA_DIR = PROJECT_ROOT / "temp-data"

# Garante que o diretório existe
TEMP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Configuração para deletar arquivo após upload bem-sucedido
DELETE_AFTER_UPLOAD = os.getenv("DELETE_AFTER_UPLOAD", "true").lower() == "true"

