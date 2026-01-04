# Makefile for the Paperless Orchestrator project

# --- Variables ---
AGENT_DIR = agents/paperless-orchestrator
DOCKER_COMPOSE_FILE = infra/docker-compose.yml
PAPERLESS_UI_DIR = paperless-ui

# --- Docker Infrastructure for Paperless-NGX ---

.PHONY: infra-up
infra-up:
	@echo "Starting Paperless-NGX infrastructure..."
	docker-compose -f $(DOCKER_COMPOSE_FILE) up -d

.PHONY: infra-down
infra-down:
	@echo "Stopping Paperless-NGX infrastructure..."
	docker-compose -f $(DOCKER_Compose_FILE) down

# --- Streamlit UI ---

.PHONY: run-ui
run-ui:
	@echo "Starting Streamlit UI with hot reloading..."
	@echo "Navigate to the local URL shown in the terminal."
	export PYTHONPATH=$(CURDIR)/src && \
	uv sync && \
	uv run streamlit run src/paperless_app/app.py

# --- Running the Agent (using local ADK installation) ---

.PHONY: run-web
run-web:
	@echo "Starting agent with ADK Web UI..."
	@echo "Navigate to http://127.0.0.1:8082 in your browser."
	@echo "Using file-based artifact service (artifacts stored in .adk/artifacts/)"
	cd $(AGENT_DIR) && uv run adk web --port=8082

.PHONY: run-web-memory
run-web-memory:
	@echo "Starting agent with ADK Web UI (in-memory artifacts)..."
	@echo "Navigate to http://127.0.0.1:8082 in your browser."
	@echo "⚠️  Artifacts will be lost when server stops!"
	cd $(AGENT_DIR) && uv run adk web --port=8082 --artifact_service_uri=memory://

.PHONY: run-api
run-api:
	@echo "Starting agent with ADK API Server..."
	@echo "Using file-based artifact service (artifacts stored in .adk/artifacts/)"
	cd $(AGENT_DIR) && uv run adk api_server

.PHONY: run-api-memory
run-api-memory:
	@echo "Starting agent with ADK API Server (in-memory artifacts)..."
	@echo "⚠️  Artifacts will be lost when server stops!"
	cd $(AGENT_DIR) && uv run adk api_server --artifact_service_uri=memory://

# --- Helper Targets ---

.PHONY: help
help:
	@echo "Available commands:"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make infra-up          - Starts the Paperless-NGX Docker containers."
	@echo "  make infra-down        - Stops the Paperless-NGX Docker containers."
	@echo ""
	@echo "Agent (Web UI):"
	@echo "  make run-web           - Runs agent with ADK web UI (file-based artifacts)."
	@echo "  make run-web-memory    - Runs agent with ADK web UI (in-memory artifacts, ephemeral)."
	@echo ""
	@echo "Agent (API Server):"
	@echo "  make run-api           - Runs agent as API server (file-based artifacts)."
	@echo "  make run-api-memory    - Runs agent as API server (in-memory artifacts, ephemeral)."
	@echo ""
	@echo "Artifact Storage:"
	@echo "  - default  : Persists artifacts in .adk/artifacts/ (recommended for dev)"
	@echo "  - memory:// : Ephemeral storage, lost on restart (for testing only)"
	@echo "  - gs://bucket-name : Google Cloud Storage (for production)"

