import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

STORE_NAME = "Loja Exemplo"
STORE_CONTEXT = """
Somos uma loja especializada em smartphones e iPhones.

Atendemos clientes interessados em compra, troca e informações sobre aparelhos.
Preços e estoque mudam frequentemente, portanto nunca devem ser inventados pela IA.
Quando uma informação comercial não estiver disponível, encaminhe para atendimento humano.
""".strip()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    demo_mode: bool = _env_bool("DEMO_MODE", True)
    ai_provider: str = os.getenv("AI_PROVIDER", "ollama").lower()
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "")
    whatsapp_token: str = os.getenv("WHATSAPP_TOKEN", "")
    whatsapp_phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    whatsapp_verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    whatsapp_api_version: str = os.getenv("WHATSAPP_API_VERSION", "")
    meta_app_secret: str = os.getenv("META_APP_SECRET", "")
    app_env: str = os.getenv("APP_ENV", "development").lower()
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()


@lru_cache
def get_settings() -> Settings:
    return Settings()
