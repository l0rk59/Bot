"""Lecture et mise en forme des prix. Les prix sont toujours des `Decimal`, jamais des `float`."""

from __future__ import annotations

import math
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
NARROW_NBSP = " "  # séparateur de milliers
NBSP = " "  # espace avant le symbole monétaire

_SPACES = re.compile(r"[\s   ']")
# « 299€95 » : le symbole sert de séparateur décimal.
_SYMBOL_AS_DECIMAL = re.compile(r"(\d)[€£$](\d{2})(?!\d)")
_NOT_NUMERIC = re.compile(r"[^0-9.,\-]")

_SYMBOLS = {"EUR": "€", "GBP": "£", "USD": "$"}


def parse_price(value: object) -> Decimal | None:
    """Convertit une valeur de prix (nombre ou texte, formats français ou anglais) en Decimal.

    Renvoie None si la valeur n'est pas un prix valide (vide, négative, illisible).
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            return None
        amount = Decimal(str(value))
    elif isinstance(value, str):
        parsed = _parse_text(value)
        if parsed is None:
            return None
        amount = parsed
    else:
        return None
    if not amount.is_finite() or amount < 0:
        return None
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def _parse_text(value: str) -> Decimal | None:
    text = _SPACES.sub("", value)
    text = _SYMBOL_AS_DECIMAL.sub(r"\1.\2", text)
    text = _NOT_NUMERIC.sub("", text)
    if not any(char.isdigit() for char in text):
        return None
    if "-" in text and (text.count("-") > 1 or not text.startswith("-")):
        return None
    try:
        return Decimal(_normalise_separators(text))
    except InvalidOperation:
        return None


def _normalise_separators(text: str) -> str:
    comma, dot = text.rfind(","), text.rfind(".")
    if comma >= 0 and dot >= 0:
        # Le dernier séparateur est le séparateur décimal : « 1.299,99 » ou « 1,299.99 ».
        decimal_pos = max(comma, dot)
        integer_part = text[:decimal_pos].replace(",", "").replace(".", "")
        return f"{integer_part}.{text[decimal_pos + 1 :]}"
    if comma >= 0:
        parts = text.split(",")
        if len(parts) > 2 or len(parts[-1]) == 3:
            return "".join(parts)  # séparateur de milliers : « 1,299 »
        return f"{parts[0]}.{parts[1]}"
    if text.count(".") > 1:
        return text.replace(".", "")  # « 1.299.000 »
    return text


def format_price(amount: Decimal, currency: str = "EUR") -> str:
    """Formate un prix à la française : « 1 299,90 € »."""
    quantized = amount.quantize(CENT, rounding=ROUND_HALF_UP)
    sign = "-" if quantized < 0 else ""
    integer, fraction = f"{abs(quantized):.2f}".split(".")
    groups: list[str] = []
    while len(integer) > 3:
        groups.insert(0, integer[-3:])
        integer = integer[:-3]
    groups.insert(0, integer)
    symbol = _SYMBOLS.get(currency.upper(), currency.upper())
    return f"{sign}{NARROW_NBSP.join(groups)},{fraction}{NBSP}{symbol}"


def percent_drop(price: Decimal, reference: Decimal) -> int:
    """Baisse en pourcentage entier : 129,90 au lieu de 1 299 donne 90."""
    if reference <= 0:
        return 0
    drop = (Decimal(1) - price / reference) * 100
    return int(drop.to_integral_value(rounding=ROUND_HALF_UP))
