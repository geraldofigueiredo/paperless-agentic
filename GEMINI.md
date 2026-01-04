# Project Overview

Paperless Orchestrator is an AI-driven document ecosystem that automates organization in Paperless-NGX. It uses Google's ADK and Gemini to analyze documents via computer vision and reconcile metadata automatically through a multi-agent system.

# Building and Running

- **Setup**: `make setup` (Uses `uv sync`)
- **Run UI**: `make run-ui`
- **Lint**: `make lint`
- **Clean**: `make clean` (Clears temp data)

# Development Conventions

- **Agents**: Defined in `src/paperless_app/agent/definition.py`.
- **Tools**: All API interactions must be `async` and located in `src/paperless_app/agent/tools/`.
- **Async**: Use `nest_asyncio` when running in Streamlit.
- **State**: Use `tool_context.state` to pass data between agents in a `SequentialAgent`.
