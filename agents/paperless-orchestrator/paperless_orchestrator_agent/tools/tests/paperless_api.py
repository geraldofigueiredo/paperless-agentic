"""
test API Tools for interacting with a Paperless-NGX instance.
"""

import os
import requests
from dotenv import load_dotenv
from paperless_orchestrator_agent.tools import paperless_api as papi

# Load environment variables from .env file
load_dotenv()


print("correspondentes: ", papi.list_correspondents())
print("criando correspondente: ", papi.create_correspondent("teste"))