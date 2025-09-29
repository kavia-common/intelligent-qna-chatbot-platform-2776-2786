import logging
import os
from typing import List, Dict

logger = logging.getLogger(__name__)


class ChatServiceError(Exception):
    """Raised when the chat service cannot process a request."""


# PUBLIC_INTERFACE
def get_chat_response(messages: List[Dict[str, str]]) -> str:
    """Generate a response using LangChain MCP + Gemini API (if configured).
    messages: A list of dicts with 'role' and 'content' fields.
    Returns the assistant response string.

    This function reads configuration from environment variables:
    - GEMINI_API_KEY: API key for Google Gemini
    - LANGCHAIN_TRACING_V2 (optional)
    - LANGCHAIN_API_KEY (optional)
    - LANGCHAIN_PROJECT (optional)
    - MCP_SERVER_URL (optional, if using an MCP gateway)
    """
    # Try to initialize external services lazily to avoid hard dependency if not configured.
    gemini_key = os.getenv("GEMINI_API_KEY")
    use_mock = os.getenv("USE_MOCK_AI", "false").lower() == "true"

    if use_mock or not gemini_key:
        # Fallback behavior for environments without keys: echo last user message.
        last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        logger.warning("Using mock AI response (no GEMINI_API_KEY provided or USE_MOCK_AI=true).")
        return f"(Mocked) I received your question: '{last_user}'. Please configure GEMINI_API_KEY for real responses."

    try:
        # Deferred imports so that CI without these packages still passes when using mock.
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        from langchain_google_genai import ChatGoogleGenerativeAI

        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        safety_settings = None  # could be extended via env

        # Instantiate the LangChain chat model for Gemini
        llm = ChatGoogleGenerativeAI(model=model_name, api_key=gemini_key, safety_settings=safety_settings)

        lc_msgs = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                lc_msgs.append(SystemMessage(content=content))
            elif role == "user":
                lc_msgs.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_msgs.append(AIMessage(content=content))
            else:
                lc_msgs.append(HumanMessage(content=content))

        resp = llm.invoke(lc_msgs)
        # resp.content is expected to be the assistant text
        return getattr(resp, "content", str(resp))
    except Exception as e:
        logger.exception("Chat service error: %s", e)
        raise ChatServiceError(str(e))
