import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, Response

from app.config import get_settings
from app.models import IncomingTextMessage, TestChatRequest, TestChatResponse
from app.services.openai_service import generate_ai_response
from app.services.whatsapp_service import send_whatsapp_message
from app.utils.logger import configure_logging, mask_phone_number
from app.utils.message_store import message_store

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(title="WhatsApp AI Sales Assistant", version="0.1.0")

FALLBACK_MESSAGE = (
    "Estou com uma instabilidade no atendimento agora. Vou deixar sua mensagem "
    "para nossa equipe continuar com você."
)


def _signature_is_valid(raw_body: bytes, signature_header: str | None) -> bool:
    if not settings.meta_app_secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.meta_app_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature_header.removeprefix("sha256="), expected)


def _extract_text_messages(payload: Any) -> list[IncomingTextMessage]:
    extracted: list[IncomingTextMessage] = []
    if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
        return extracted

    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes", []):
            if not isinstance(change, dict) or change.get("field") != "messages":
                continue
            value = change.get("value", {})
            if not isinstance(value, dict):
                continue
            contacts = value.get("contacts", [])
            name = None
            if contacts and isinstance(contacts[0], dict):
                profile = contacts[0].get("profile", {})
                if isinstance(profile, dict):
                    name = profile.get("name")
            for message in value.get("messages", []):
                if not isinstance(message, dict) or message.get("type") != "text":
                    continue
                text_data = message.get("text", {})
                phone = message.get("from")
                message_id = message.get("id")
                text = text_data.get("body") if isinstance(text_data, dict) else None
                if all(isinstance(item, str) and item.strip() for item in (phone, message_id, text)):
                    extracted.append(
                        IncomingTextMessage(
                            phone_number=phone,
                            customer_name=name if isinstance(name, str) else None,
                            message_id=message_id,
                            text=text,
                        )
                    )
    return extracted


async def _process_message(message: IncomingTextMessage) -> None:
    logger.info(
        "Mensagem recebida | remetente=%s | message_id=%s | texto=%s",
        mask_phone_number(message.phone_number),
        message.message_id,
        message.text,
    )
    try:
        answer = await generate_ai_response(message.text, message.customer_name)
    except Exception:
        logger.exception("Falha ao gerar resposta para message_id=%s", message.message_id)
        answer = FALLBACK_MESSAGE
    await send_whatsapp_message(message.phone_number, answer)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Response:
    if (
        hub_mode == "subscribe"
        and settings.whatsapp_verify_token
        and hmac.compare_digest(hub_verify_token or "", settings.whatsapp_verify_token)
        and hub_challenge is not None
    ):
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks) -> dict[str, str]:
    raw_body = await request.body()
    if not _signature_is_valid(raw_body, request.headers.get("x-hub-signature-256")):
        logger.warning("Webhook rejeitado: assinatura inválida")
        raise HTTPException(status_code=401, detail="Invalid signature")

    logger.info("Webhook recebido")
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Payload inválido recebido no webhook")
        return {"status": "ignored"}

    for message in _extract_text_messages(payload):
        if await message_store.mark_if_new(message.message_id):
            background_tasks.add_task(_process_message, message)
        else:
            logger.info("Mensagem duplicada ignorada: message_id=%s", message.message_id)
    return {"status": "received"}


if settings.app_env == "development":
    @app.post("/test-chat", response_model=TestChatResponse)
    async def test_chat(body: TestChatRequest) -> TestChatResponse:
        try:
            answer = await generate_ai_response(body.message)
            return TestChatResponse(response=answer)
        except Exception:
            logger.exception("Falha no endpoint de teste")
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable")
