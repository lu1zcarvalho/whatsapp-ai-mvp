import logging

from app.config import get_settings


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, get_settings().log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def mask_phone_number(phone_number: str) -> str:
    if len(phone_number) <= 4:
        return "*" * len(phone_number)
    return f"{'*' * (len(phone_number) - 4)}{phone_number[-4:]}"
