import logging

import httpx

from app.config import get_settings
from app.prompts.sales_assistant import build_system_prompt

logger = logging.getLogger(__name__)


async def generate_ollama_response(
    customer_message: str,
    customer_name: str | None = None,
    conversation: list[dict[str, str]] | None = None,
    instructions: str | None = None,
) -> str:
    settings = get_settings()
    if not settings.ollama_model:
        raise RuntimeError("OLLAMA_MODEL não configurado")

    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    messages = [
        {"role": "system", "content": instructions or build_system_prompt(customer_name)}
    ]
    messages.extend(conversation or [{"role": "user", "content": customer_message}])
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": 220,
            "temperature": 0.35,
            "top_p": 0.85,
            "repeat_penalty": 1.12,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.ConnectError as exc:
        raise RuntimeError(
            "Não foi possível conectar ao Ollama. Confirme se ele está em execução."
        ) from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise RuntimeError(
            f"Ollama retornou status {exc.response.status_code}: {detail}"
        ) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Falha na comunicação com o Ollama: {exc}") from exc

    data = response.json()
    message = data.get("message", {}) if isinstance(data, dict) else {}
    answer = message.get("content", "") if isinstance(message, dict) else ""
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("O Ollama retornou uma resposta vazia")
    return answer.strip()
