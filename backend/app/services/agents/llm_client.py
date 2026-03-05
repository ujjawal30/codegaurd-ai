"""
CodeGuard AI — Centralized LLM Client.

Provides configured Gemini chat model and embeddings via LangChain,
with retry logic and token tracking.
"""

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from pydantic import SecretStr
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_chat_model(temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    """
    Return a configured Gemini chat model.

    Args:
        temperature: Sampling temperature (0.0 = deterministic).

    Returns:
        Configured ChatGoogleGenerativeAI instance.
    """
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL_NAME,
        google_api_key=SecretStr(settings.GEMINI_API_KEY),
        temperature=temperature,
        max_output_tokens=8192,
        convert_system_message_to_human=False,
    )


def get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    """Return a configured Gemini embeddings model."""
    return GoogleGenerativeAIEmbeddings(
        model=settings.GEMINI_EMBED_MODEL_NAME,
        api_key=SecretStr(settings.GEMINI_API_KEY),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(Exception),
    before_sleep=lambda retry_state: logger.warning(
        "llm_retry",
        attempt=retry_state.attempt_number,
        error=str(retry_state.outcome.exception()) if retry_state.outcome else "unknown",
    ),
)
async def invoke_with_retry(model: ChatGoogleGenerativeAI, messages: list) -> str:
    """
    Invoke the chat model with retry logic.

    Retries up to 3 times with exponential backoff on any exception
    (rate limits, transient errors, etc.).

    Args:
        model: ChatGoogleGenerativeAI instance.
        messages: List of LangChain message objects.

    Returns:
        String content from the model response.
    """
    response = await model.ainvoke(messages)
    content = response.content

    if isinstance(content, str):
        return content

    # Gemini can return content as a list of content blocks:
    # [{'type': 'text', 'text': '...'}, ...]
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item))
        return "".join(parts)

    return str(content)
