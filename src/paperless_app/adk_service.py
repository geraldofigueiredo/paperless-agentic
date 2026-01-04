import streamlit as st
import asyncio
import time
import os
import sys
import logging
import traceback

# Custom Log Handler for Streamlit
class StreamlitLogHandler(logging.Handler):
    def emit(self, record):
        try:
            # Check if we are in a Streamlit context and if session_state is available
            # We initialize the log list here to ensure it exists across different sessions
            if "debug_logs" not in st.session_state:
                st.session_state.debug_logs = []
            
            log_entry = self.format(record)
            st.session_state.debug_logs.append(log_entry)
            
            # Keep only the last 100 logs
            if len(st.session_state.debug_logs) > 100:
                st.session_state.debug_logs.pop(0)
        except (AttributeError, RuntimeError, KeyError):
            # If st.session_state is not accessible (e.g. called from a separate thread 
            # or before Streamlit is fully ready), we just skip it to avoid crashing.
            pass

# Configure basic logging
logger = logging.getLogger("paperless_app")
logger.setLevel(logging.INFO)

# Clear existing handlers to avoid duplicates on rerun
if logger.handlers:
    logger.handlers.clear()

# Add standard stream handler
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(stream_handler)

# Add Streamlit handler
st_handler = StreamlitLogHandler()
st_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(st_handler)

from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types as genai_types
from paperless_app.agent.definition import root_agent

APP_NAME_FOR_ADK = "paperless_orchestrator_app"
USER_ID = "streamlit_user"
ADK_SESSION_KEY = "adk_session_id"

@st.cache_resource
def get_runner():
    """Initializes and caches the ADK Runner."""
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME_FOR_ADK,
        session_service=session_service
    )
    return runner, session_service

def initialize_adk():
    """
    Initializes the Google ADK Runner and manages the ADK session.
    """
    runner, session_service = get_runner()
    
    if ADK_SESSION_KEY not in st.session_state:
        session_id = f"streamlit_adk_session_{int(time.time())}_{os.urandom(4).hex()}"
        st.session_state[ADK_SESSION_KEY] = session_id
        logger.info(f"Creating new ADK session: {session_id}")
        
        asyncio.run(session_service.create_session(
            app_name=APP_NAME_FOR_ADK,
            user_id=USER_ID,
            session_id=session_id
        ))
    else:
        session_id = st.session_state[ADK_SESSION_KEY]
        logger.info(f"Using existing ADK session: {session_id}")
        
        session_exists = asyncio.run(session_service.get_session(
            app_name=APP_NAME_FOR_ADK, user_id=USER_ID, session_id=session_id
        ))
        if not session_exists:
            logger.warning(f"Session {session_id} not found in service, recreating...")
            asyncio.run(session_service.create_session(
                app_name=APP_NAME_FOR_ADK,
                user_id=USER_ID,
                session_id=session_id
            ))
    return runner, session_id

async def run_adk_async(runner: Runner, session_id: str, user_message_text: str):
    """
    Asynchronously runs a single turn of the ADK agent conversation.
    """
    logger.info(f"Running agent turn for session {session_id}")
    
    session = await runner.session_service.get_session(app_name=APP_NAME_FOR_ADK, user_id=USER_ID, session_id=session_id)
    if not session:
        error_msg = "Error: ADK session not found."
        logger.error(error_msg)
        return error_msg

    content = genai_types.Content(role='user', parts=[genai_types.Part(text=user_message_text)])
    final_response_text = "[Agent did not provide a response]"

    try:
        async for event in runner.run_async(user_id=USER_ID, session_id=session_id, new_message=content):
            # Log all events for debugging
            event_type = type(event).__name__
            logger.info(f"ADK Event: {event_type}")
            
            if event.is_final_response():
                if event.content and event.content.parts and hasattr(event.content.parts[0], 'text'):
                    final_response_text = event.content.parts[0].text
                    logger.info(f"Agent response received: {final_response_text[:50]}...")
                # Do NOT break here, as there might be more events or internal transitions
            
            elif hasattr(event, 'tool_call') and event.tool_call:
                logger.info(f"Tool call: {event.tool_call.function_call.name}")
            
            elif hasattr(event, 'tool_response') and event.tool_response:
                logger.info(f"Tool response received for: {event.tool_response.function_response.name}")

    except Exception as e:
        full_traceback = traceback.format_exc()
        logger.error(f"ADK Runner failed: {str(e)}\n{full_traceback}")
        final_response_text = f"**Agent Error:**\n\n```\n{e}\n```\n\n*Check the debug logs for more details.*"
        
    return final_response_text

def run_adk_sync(runner: Runner, session_id: str, user_message_text: str) -> str:
    """
    Synchronous wrapper for running ADK by managing the event loop.
    """
    try:
        # Improved loop management for Streamlit
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            # If we are in an environment where the loop is already running (like some versions of Streamlit)
            # we might need a different approach, but usually streamlit threads don't have a running loop.
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(run_adk_async(runner, session_id, user_message_text))
        else:
            return loop.run_until_complete(run_adk_async(runner, session_id, user_message_text))
    except Exception as e:
        logger.error(f"Error in run_adk_sync: {str(e)}", exc_info=True)
        return f"**System Error:** {str(e)}"

def reset_adk_session():
    """
    Clears the current ADK session from Streamlit state to force a new one.
    """
    if ADK_SESSION_KEY in st.session_state:
        old_session = st.session_state[ADK_SESSION_KEY]
        del st.session_state[ADK_SESSION_KEY]
        logger.info(f"ADK session {old_session} reset.")
