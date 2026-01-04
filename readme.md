# 🤖 Paperless Agentic

**An Agentic AI Ecosystem for Document Intelligence in Paperless-NGX**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Google ADK](https://img.shields.io/badge/AI-Google_ADK-red.svg)](https://github.com/google/ai-agent-sdk)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Paperless-NGX](https://img.shields.io/badge/DMS-Paperless--NGX-green.svg)](https://docs.paperless-ngx.com/)

**Paperless Agentic** is a cutting-edge document ecosystem that transforms static file storage into an autonomous workspace. Powered by **Google Gemini Vision** and orchestrated via the **Agent Development Kit (ADK)**, it uses a multi-agent system to "see", understand, and organize your documents with zero manual effort.

---

## 🚀 Key Features

- **Multi-Agent Ingestion Workflow**: A specialized sequence of agents that analyze, categorize, and upload documents with zero manual entry.
- **Vision-Powered Analysis**: Leverages Google Gemini's native vision capabilities to "read" and understand document content (invoices, resumes, contracts) directly from images and PDFs.
- **Smart Entity Resolution**: Intelligently matches extracted data with existing correspondents, tags, and document types using fuzzy matching and normalization logic.
- **Natural Language Querying**: Talk to your documents. The search agent translates your questions into complex Paperless-NGX API filters.
- **Real-Time Debugging UI**: A premium Streamlit interface featuring live agent event tracking and session-isolated execution.

---

## 🧠 Cognitive Architecture (AI Agents)

The project showcases advanced agentic patterns using a hierarchical and sequential multi-agent design:

### 1. The Root Agent
The primary entry point. It understands user intent and routes tasks to specialized sub-agents.

### 2. Ingestion Pipeline (`SequentialAgent`)
This is where the magic happens. When a file is uploaded, three agents work in lockstep:
*   **Document Analyzer**: Uses Vision + OCR to extract titles, dates, companies, and keywords.
*   **Metadata Creator**: The "Reconciler". It lists existing tags and correspondents, performing smart matching (normalization + Jaccard similarity) to avoid duplicates and ensure a clean database.
*   **Document Uploader**: The final step. It compiles all gathered IDs and files to perform a multi-part POST request to the Paperless API.

### 3. Search Agent
Capable of listing, searching, and detailing documents via natural language.

---

## 🛠️ Tech Stack

- **Large Language Model**: Google Gemini (via Vertex AI / Google AI Studio).
- **Agent Orchestration**: Google Agent Development Kit (ADK).
- **Backend Framework**: Python 3.10+ / Asyncio.
- **Frontend**: Streamlit with custom `nest_asyncio` integration for robust event loops.
- **Communication**: REST API (httpx) with Paperless-NGX.

---

## 📋 Installation & Setup

### Prerequisites
- Python 3.10 or higher.
- A running instance of **Paperless-NGX**.
- A **Google Gemini API Key**.

### Steps
1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/paperless-agentic.git
   cd paperless-agentic
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the root:
   ```env
   PAPERLESS_URL=your_paperless_url
   PAPERLESS_API_TOKEN=your_token
   GOOGLE_API_KEY=your_gemini_key
   ```

3. **Install Dependencies**:
   ```bash
   make setup
   # or
   pip install .
   ```

4. **Run the UI**:
   ```bash
   make run-ui
   ```

---

## 🏗️ Technical Expertise: Challenges Overcome

During the development of **Paperless Agentic**, several critical agentic design challenges were solved:
- **State Management in Streamlit**: Implemented a session-isolated reset mechanism to ensure that each document ingestion starts with a clean slate, preventing context leakage between unrelated files.
- **Async Event Loop Harmony**: Solved the "Loop already running" conflict in Streamlit using `nest_asyncio` and custom runner wrappers, allowing the ADK's asynchronous events to stream directly to the UI.
- **Tool-State Bridging**: Designed specialized tools that bridge the gap between the LLM's reasoning and the Paperless API requirements, ensuring IDs are persisted across sub-agent transitions.

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

---

*Developed by [Geraldo Figueiredo](https://github.com/geraldofigueiredo)*
