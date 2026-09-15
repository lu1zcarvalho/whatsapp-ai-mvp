import asyncio
import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from app.config import get_settings
from app.services.ai_service import generate_ai_response


@dataclass(frozen=True)
class Product:
    model: str
    storage: int
    price: Decimal

    @property
    def label(self) -> str:
        return f"{self.model} {self.storage}GB"


CATALOG = (
    Product("iPhone 13", 128, Decimal("3299")),
    Product("iPhone 14", 128, Decimal("3899")),
    Product("iPhone 15", 128, Decimal("4699")),
    Product("iPhone 15 Pro", 128, Decimal("6499")),
    Product("iPhone 15 Pro", 256, Decimal("7199")),
    Product("iPhone 16", 128, Decimal("5599")),
    Product("iPhone 16 Pro", 128, Decimal("7499")),
)


@dataclass
class SessionState:
    history: list[dict[str, str]] = field(default_factory=list)
    candidates: list[Product] = field(default_factory=list)
    selected: Product | None = None
    color: str | None = None


_sessions: dict[str, SessionState] = {}
_lock = asyncio.Lock()


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _money(value: Decimal) -> str:
    formatted = f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}"
    return f"R$ {formatted.replace(',', 'X').replace('.', ',').replace('X', '.')}"


def _find_products(text: str, state: SessionState) -> list[Product]:
    normalized = _normalize(text)
    model_match = re.search(r"(?:iphone\s*)?(13|14|15|16)(?:\s*(pro))?", normalized)
    storage_match = re.search(r"\b(128|256)\s*(?:gb|g)?\b", normalized)

    if model_match:
        number, pro = model_match.groups()
        model = f"iPhone {number}{' Pro' if pro else ''}"
        matches = [product for product in CATALOG if product.model == model]
    elif state.candidates:
        matches = list(state.candidates)
    elif state.selected:
        matches = [state.selected]
    else:
        matches = []

    if storage_match:
        storage = int(storage_match.group(1))
        narrowed = [product for product in matches if product.storage == storage]
        if narrowed:
            matches = narrowed
    return matches


def _product_lines(products: list[Product]) -> str:
    return "\n".join(f"• {product.label} — {_money(product.price)}" for product in products)


def _update_state(message: str, state: SessionState) -> list[Product]:
    text = _normalize(message)
    products = _find_products(message, state)
    if products:
        state.candidates = products
        if len(products) == 1:
            state.selected = products[0]

    colors = ("preto", "branco", "azul", "rosa", "verde", "dourado", "natural")
    mentioned_color = next((color for color in colors if color in text), None)
    if mentioned_color:
        state.color = mentioned_color
    return products


def _sales_instructions(state: SessionState) -> str:
    catalog_lines = []
    for product in CATALOG:
        pix = product.price * Decimal("0.95")
        installment = product.price / Decimal("12")
        catalog_lines.append(
            f"- {product.label}: preço {_money(product.price)}; "
            f"PIX {_money(pix)}; 12x de {_money(installment)}"
        )

    selected = state.selected.label if state.selected else "ainda não definido"
    candidates = ", ".join(product.label for product in state.candidates) or "nenhum"
    color = state.color or "ainda não definida"
    return f"""
Você é uma atendente comercial humana da Prime iPhones conversando por chat.

COMO RESPONDER:
- Use português brasileiro natural, simpático e seguro.
- Seja breve: normalmente 2 a 4 frases. Não dê respostas genéricas ou discursos.
- Responda primeiro à pergunta e termine com apenas uma pergunta útil.
- Use o histórico. Não pergunte novamente algo que o cliente já informou.
- Entenda modelo, armazenamento, cor, pagamento e intenção de compra.
- Não diga que é IA, modelo de linguagem ou assistente virtual.
- Evite frases burocráticas como “não possuo informações” e “consulte representantes”.
- Não diga que entrará em contato. Apenas ofereça chamar uma atendente.

REGRAS OBRIGATÓRIAS:
- Use somente o catálogo abaixo. Nunca altere números nem invente produtos, preços ou cores.
- Produto no catálogo não confirma estoque físico.
- NUNCA escreva “está disponível”, “temos em estoque” ou confirme uma cor. Diga que a
  opção está no catálogo e que a disponibilidade da unidade e da cor será confirmada.
- Se perguntarem “tem?”, mostre todas as opções correspondentes com preço e avise brevemente
  que a disponibilidade da unidade ou cor será confirmada.
- PIX tem 5% de desconto. Cartão em até 12x, sujeito às condições da loja.
- Os valores já estão calculados abaixo: copie-os exatamente, não refaça as contas.
- Quando houver mais de um armazenamento, mostre todos e pergunte qual prefere.
- Se o cliente disser “quero comprar”, “vou levar” ou “fechar”, inclua exatamente:
  “posso chamar uma atendente para finalizar sua compra 😊”

CATÁLOGO E CÁLCULOS:
{chr(10).join(catalog_lines)}

CONTEXTO IDENTIFICADO PELO SISTEMA:
- Produto selecionado: {selected}
- Opções relacionadas: {candidates}
- Cor mencionada: {color}

EXEMPLO DO TOM ESPERADO:
Cliente: tem iphone 15 pro?
Atendente: Temos duas opções no catálogo: iPhone 15 Pro 128GB por R$ 6.499,00 e 256GB
por R$ 7.199,00. Qual armazenamento você prefere? Confirmo a disponibilidade da unidade
e da cor escolhida para você.
""".strip()


def _enforce_commercial_rules(
    message: str,
    state: SessionState,
    reply: str,
) -> str:
    """Impede que um modelo local pequeno confirme estoque ou omita fatos essenciais."""
    safe_reply = re.sub(
        r"\best[aá]\s+dispon[ií]vel(?:\s+para\s+compra)?\b",
        "está no nosso catálogo; a disponibilidade da unidade e da cor precisa ser confirmada",
        reply,
        flags=re.IGNORECASE,
    )
    safe_reply = re.sub(
        r"\btemos\s+em\s+estoque\b",
        "temos como opção no catálogo, com disponibilidade a confirmar",
        safe_reply,
        flags=re.IGNORECASE,
    )

    normalized_message = _normalize(message)
    wants_pix = "pix" in normalized_message
    wants_installments = any(
        term in normalized_message for term in ("12x", "12 x", "parcela")
    )
    if wants_pix or wants_installments:
        return _demo_reply(message, state)

    hot_lead = any(
        term in normalized_message
        for term in ("quero comprar", "vou levar", "fechar", "finalizar")
    )
    mentions_choice = bool(
        state.color and state.color in normalized_message
    ) or bool(re.search(r"\b(128|256)\s*(?:gb|g)?\b", normalized_message))
    if hot_lead or mentions_choice:
        return _demo_reply(message, state)

    asks_availability = any(
        term in normalized_message for term in ("tem ", "disponivel", "estoque")
    )
    products = _find_products(message, state)
    if asks_availability and products:
        missing_product = any(product.label not in safe_reply for product in products)
        if missing_product:
            safe_reply = (
                "Temos estas opções no catálogo:\n"
                + _product_lines(products)
                + "\nQual armazenamento você prefere? A disponibilidade da unidade e da cor "
                "escolhida precisa ser confirmada."
            )
        elif "disponibilidade" not in _normalize(safe_reply):
            safe_reply += "\nA disponibilidade da unidade e da cor escolhida precisa ser confirmada."

    return safe_reply.strip()


def _demo_reply(message: str, state: SessionState) -> str:
    text = _normalize(message)
    products = _update_state(message, state)
    mentioned_color = bool(state.color and state.color in text)

    hot_lead = any(term in text for term in ("quero comprar", "vou levar", "fechar", "finalizar"))
    if hot_lead:
        detail = "seu interesse"
        if state.selected:
            detail = f"o {state.selected.label}"
            if state.color:
                detail += f" na cor {state.color}"
        return (
            f"Perfeito! Anotei {detail}. "
            "posso chamar uma atendente para finalizar sua compra 😊"
        )

    wants_pix = "pix" in text
    wants_installments = "12x" in text or "12 x" in text or "parcela" in text
    if wants_pix or wants_installments:
        if not products:
            return "Claro! Qual modelo e armazenamento você quer calcular?"
        lines: list[str] = []
        for product in products:
            if wants_pix:
                total = product.price * Decimal("0.95")
                lines.append(f"• {product.label}: {_money(total)} no PIX (5% de desconto)")
            else:
                installment = product.price / Decimal("12")
                lines.append(f"• {product.label}: 12x de aproximadamente {_money(installment)}")
        suffix = (
            "\nO parcelamento está sujeito às condições da loja."
            if wants_installments
            else ""
        )
        return "Fica assim:\n" + "\n".join(lines) + suffix

    if mentioned_color or re.search(r"\b(128|256)\s*(?:gb|g)?\b", text):
        if len(products) == 1:
            product = products[0]
            color_text = f" na cor {state.color}" if state.color else ""
            return (
                f"Ótima escolha! Anotei {product.label}{color_text}, por {_money(product.price)}. "
                "A disponibilidade da cor precisa ser confirmada. Prefere PIX ou cartão?"
            )
        if products:
            return "Encontrei estas opções:\n" + _product_lines(products) + "\nQual delas você prefere?"

    asks_availability = any(term in text for term in ("tem ", "disponivel", "catalogo", "opcoes"))
    if asks_availability:
        if products:
            return (
                "Estas são as opções no nosso catálogo:\n"
                + _product_lines(products)
                + "\nQual armazenamento você prefere? A disponibilidade precisa ser confirmada."
            )
        return (
            "Hoje trabalhamos com iPhones 13, 14, 15 e 16, incluindo versões Pro. "
            "Qual modelo você procura?"
        )

    if any(term in text for term in ("oi", "ola", "bom dia", "boa tarde", "boa noite")):
        return "Olá! 😊 Sou a assistente virtual da WD iPhones. Qual modelo você está procurando?"

    if "preco" in text or "quanto" in text or "valor" in text:
        if products:
            return "No catálogo temos:\n" + _product_lines(products) + "\nVocê prefere PIX ou cartão?"
        return "Consigo calcular para você 😊 Qual modelo e armazenamento deseja?"

    return (
        "Entendi! Para te ajudar melhor, me diga o modelo, armazenamento, cor desejada "
        "e se prefere pagar no PIX ou cartão."
    )


async def chat(session_id: str, message: str) -> str:
    async with _lock:
        state = _sessions.setdefault(session_id, SessionState())
        state.history.append({"role": "user", "content": message})

        if get_settings().demo_mode:
            reply = _demo_reply(message, state)
        else:
            _update_state(message, state)
            recent = state.history[-12:]
            reply = await generate_ai_response(
                message,
                conversation=recent,
                instructions=_sales_instructions(state),
            )
            reply = _enforce_commercial_rules(message, state, reply)

        state.history.append({"role": "assistant", "content": reply})
        state.history = state.history[-20:]
        return reply


async def reset_session(session_id: str) -> None:
    async with _lock:
        _sessions.pop(session_id, None)
