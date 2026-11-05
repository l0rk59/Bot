from decimal import Decimal

import pytest

from pricebot.prices import format_price, parse_price, percent_drop


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("129.9", "129.90"),
        ("1299.95", "1299.95"),
        ("1 299,99 €", "1299.99"),
        ("1 299,99 €", "1299.99"),
        ("1 299,99 €", "1299.99"),
        ("1.299,99", "1299.99"),
        ("1,299.99", "1299.99"),
        ("1,299", "1299.00"),
        ("12,5", "12.50"),
        ("299€95", "299.95"),
        ("1 990€00", "1990.00"),
        ("EUR 49.90", "49.90"),
        ("0", "0.00"),
        ("0.01", "0.01"),
        (788, "788.00"),
        (749.5, "749.50"),
        (Decimal("10.005"), "10.01"),
    ],
)
def test_parse_price_accepts_common_formats(value: object, expected: str) -> None:
    assert parse_price(value) == Decimal(expected)


@pytest.mark.parametrize(
    "value",
    [None, "", "   ", "gratuit", "-5", "12-3", True, float("nan"), float("inf"), [], {}],
)
def test_parse_price_rejects_invalid_values(value: object) -> None:
    assert parse_price(value) is None


def test_format_price_uses_french_conventions() -> None:
    assert format_price(Decimal("1299.9")) == "1 299,90 €"
    assert format_price(Decimal("129.9")) == "129,90 €"
    assert format_price(Decimal("1234567")) == "1 234 567,00 €"
    assert format_price(Decimal("5"), "GBP") == "5,00 £"
    assert format_price(Decimal("5"), "CHF") == "5,00 CHF"


def test_percent_drop() -> None:
    assert percent_drop(Decimal("129.90"), Decimal("1299")) == 90
    assert percent_drop(Decimal("100"), Decimal("100")) == 0
    assert percent_drop(Decimal("10"), Decimal("0")) == 0
