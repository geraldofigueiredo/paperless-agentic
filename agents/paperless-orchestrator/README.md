# Paperless Orchestrator Agent

This agent, built following the Google ADK architectural pattern, serves as an intelligent assistant for interacting with a [Paperless-NGX](https://github.com/paperless-ngx/paperless-ngx) instance.

## Features

- **Document Ingestion**: Upload new documents (PDFs, images) and let the agent extract metadata and classify them intelligently.
- **Document Search**: Ask the agent in natural language to find documents for you.
- **Automated Backups**: A separate script provides a robust way to back up your documents to a cloud provider (AWS S3 or GCS).

## Setup

1.  **Clone the repository and navigate to this directory.**

2.  **Configure your environment:**
    -   Copy the `.env.example` file to `.env`.
    -   Fill in the required values in the `.env` file, including your Gemini API Key, Paperless-NGX URL and API token, and backup provider settings.

3.  **Install dependencies:**
    ```bash
    pip install -e .
    ```
    or using `uv`:
    ```bash
    uv pip install -e .
    ```

4.  **Run the agent:**
    ```bash
    # (Instructions to be added once main.py is implemented)
    ```
