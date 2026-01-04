from paperless_app.adk_service import initialize_adk, run_adk_sync, reset_adk_session
from paperless_app.config import TEMP_DATA_DIR
import streamlit as st
import os
import uuid

MESSAGE_HISTORY_KEY = "paperless_messages"

def handle_pdf_upload(uploaded_file, adk_runner, session_id):
    """Saves the uploaded PDF to the temp-data folder and triggers the ingestion agent."""
    if uploaded_file is not None:
        try:
            # Reset ADK session to start with a clean state for the new document
            reset_adk_session()
            
            # Re-initialize to get a new runner and session_id
            adk_runner, session_id = initialize_adk()
            
            os.makedirs(TEMP_DATA_DIR, exist_ok=True)
            
            unique_filename = f"{uuid.uuid4()}.pdf"
            file_path = os.path.join(TEMP_DATA_DIR, unique_filename)
            
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            st.sidebar.success(f"File '{uploaded_file.name}' saved as '{unique_filename}'.")
            
            initial_prompt = f"Processar o arquivo: {unique_filename}"
            
            st.session_state[MESSAGE_HISTORY_KEY].append({"role": "user", "content": f"Arquivo '{uploaded_file.name}' enviado para processamento."})
            
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                with st.spinner("Agente está processando o documento..."):
                    agent_response = run_adk_sync(adk_runner, session_id, initial_prompt)
                    message_placeholder.markdown(agent_response)
            
            st.session_state[MESSAGE_HISTORY_KEY].append({"role": "assistant", "content": agent_response})
            st.rerun()

        except Exception as e:
            st.sidebar.error(f"Erro ao salvar o arquivo: {e}")

def run_streamlit_app():
    """Sets up and runs the Streamlit web application."""
    st.set_page_config(page_title="Paperless Orchestrator", layout="wide")
    st.title("📄 Paperless Orchestrator Assistant")

    adk_runner, session_id = initialize_adk()

    with st.sidebar:
        st.header("Upload de Documentos")
        uploaded_file = st.file_uploader("Selecione um arquivo PDF para enviar ao Paperless-NGX", type="pdf")
        if st.button("Processar Arquivo"):
            if uploaded_file:
                handle_pdf_upload(uploaded_file, adk_runner, session_id)
            else:
                st.sidebar.warning("Por favor, selecione um arquivo PDF primeiro.")
        
        st.divider()
        st.header("Ferramentas de Debug")
        with st.expander("Visualizar Logs"):
            if "debug_logs" in st.session_state and st.session_state.debug_logs:
                for log in reversed(st.session_state.debug_logs):
                    st.text(log)
            else:
                st.info("Nenhum log disponível ainda.")
            
            if st.button("Limpar Logs"):
                st.session_state.debug_logs = []
                st.rerun()
            
            if st.button("Resetar Sessão de IA"):
                reset_adk_session()
                if MESSAGE_HISTORY_KEY in st.session_state:
                    st.session_state[MESSAGE_HISTORY_KEY] = []
                st.success("Sessão resetada com sucesso!")
                st.rerun()

    st.header("Chat Interativo")
    if MESSAGE_HISTORY_KEY not in st.session_state:
        st.session_state[MESSAGE_HISTORY_KEY] = []

    for message in st.session_state[MESSAGE_HISTORY_KEY]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Faça uma pergunta sobre seus documentos..."):
        st.session_state[MESSAGE_HISTORY_KEY].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Pensando..."):
                agent_response = run_adk_sync(adk_runner, session_id, prompt)
                message_placeholder.markdown(agent_response)
        
        st.session_state[MESSAGE_HISTORY_KEY].append({"role": "assistant", "content": agent_response})
        st.rerun()

if __name__ == "__main__":
    run_streamlit_app()
