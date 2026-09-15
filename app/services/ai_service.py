import logging

from app.config import get_settings
from app.services.ollama_service import generate_ollama_response
from app.services.openai_service import generate_openai_response

logger = logging.getLogger(__name__)


async def generate_ai_response(
    customer_message: str,
    customer_name: str | None = None,
    conversation: list[dict[str, str]] | None = None,
    instructions: str | None = None,
) -> str:
    settings = get_settings()
    logger.info("Chamada da IA iniciada | provider=%s", settings.ai_provider)

    if settings.ai_provider == "ollama":
        answer = await generate_ollama_response(
            customer_message, customer_name, conversation, instructions
        )
    elif settings.ai_provider == "openai":
        answer = await generate_openai_response(
            customer_message, customer_name, conversation, instructions
        )
    else:
        raise RuntimeError(
            f"AI_PROVIDER inválido: {settings.ai_provider}. Use 'ollama' ou 'openai'."
        )

    logger.info("Resposta da IA gerada: %s", answer)
    return answer
