import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


async def send_whatsapp_message(phone_number: str, message: str) -> bool:
    settings = get_settings()
    if not all(
        (
            settings.whatsapp_token,
            settings.whatsapp_phone_number_id,
            settings.whatsapp_api_version,
        )
    ):
        logger.error("Credenciais do WhatsApp não configuradas")
        return False

    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
        if response.is_success:
            logger.info("Mensagem enviada para o WhatsApp (status=%s)", response.status_code)
            return True
        logger.error(
            "Falha na API do WhatsApp (status=%s): %s",
            response.status_code,
            response.text[:1000],
        )
    except httpx.HTTPError as exc:
        logger.exception("Erro de rede ao enviar mensagem ao WhatsApp: %s", exc)
    return False
