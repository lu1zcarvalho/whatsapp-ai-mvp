import logging

from openai import AsyncOpenAI

from app.config import get_settings
from app.prompts.sales_assistant import build_system_prompt

logger = logging.getLogger(__name__)


async def generate_openai_response(
    customer_message: str,
    customer_name: str | None = None,
    conversation: list[dict[str, str]] | None = None,
    instructions: str | None = None,
) -> str:
    settings = get_settings()
    if not settings.openai_api_key or not settings.openai_model:
        raise RuntimeError("OPENAI_API_KEY ou OPENAI_MODEL não configurada")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.responses.create(
        model=settings.openai_model,
        instructions=instructions or build_system_prompt(customer_name),
        input=conversation or customer_message,
        max_output_tokens=300,
        store=False,
    )
    answer = response.output_text.strip()
    if not answer:
        raise RuntimeError("A OpenAI retornou uma resposta vazia")
    return answer
