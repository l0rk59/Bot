from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pricebot.detection import DetectionSettings, decimal_shift, evaluate, time_weighted_median
from pricebot.models import Availability
from pricebot.storage import PricePoint

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
SETTINGS = DetectionSettings()


def point(days_ago: float, price: str) -> PricePoint:
    return PricePoint(NOW - timedelta(days=days_ago), Decimal(price), Availability.IN_STOCK)


def test_time_weighted_median_ignores_short_promotions() -> None:
    history = [point(30, "1299"), point(2, "999"), point(1.9, "1299")]  # promo de 2 h 24
    assert time_weighted_median(history, NOW) == Decimal("1299")


def test_time_weighted_median_follows_a_lasting_price_change() -> None:
    history = [point(30, "1299"), point(20, "1099")]  # baisse durable depuis 20 jours
    assert time_weighted_median(history, NOW) == Decimal("1099")


def test_time_weighted_median_edge_cases() -> None:
    assert time_weighted_median([], NOW) is None
    assert time_weighted_median([point(0, "50")], NOW) == Decimal("50")


def test_decimal_shift() -> None:
    tolerance = Decimal("0.10")
    assert decimal_shift(Decimal("129.90"), Decimal("1299"), tolerance) == 10
    assert decimal_shift(Decimal("12.99"), Decimal("1299"), tolerance) == 100
    assert decimal_shift(Decimal("1.29"), Decimal("1299"), tolerance) == 1000
    assert decimal_shift(Decimal("600"), Decimal("1299"), tolerance) is None
    assert decimal_shift(Decimal("0"), Decimal("1299"), tolerance) is None


def test_evaluate_flags_a_decimal_shift() -> None:
    verdict = evaluate(Decimal("129.90"), Decimal("1299.00"), SETTINGS)
    assert verdict is not None
    assert verdict.reasons[0] == "virgule décalée (×10)"
    assert "-90 % par rapport au prix habituel" in verdict.reasons[1]
    assert verdict.saving == Decimal("1169.10")


def test_evaluate_flags_a_big_drop() -> None:
    verdict = evaluate(Decimal("400"), Decimal("1000"), SETTINGS)
    assert verdict is not None
    assert len(verdict.reasons) == 1
    assert verdict.ratio == Decimal("0.4")


def test_evaluate_flags_a_symbolic_price() -> None:
    verdict = evaluate(Decimal("1.00"), Decimal("349"), SETTINGS)
    assert verdict is not None
    assert "prix symbolique" in verdict.reasons


def test_evaluate_ignores_normal_promotions_and_small_savings() -> None:
    assert evaluate(Decimal("700"), Decimal("1000"), SETTINGS) is None  # -30 % : promo normale
    assert evaluate(Decimal("20"), Decimal("45"), SETTINGS) is None  # -55 % mais 25 € seulement
    assert evaluate(Decimal("100"), None, SETTINGS) is None  # pas encore d'historique
    assert evaluate(Decimal("100"), Decimal("0"), SETTINGS) is None


def test_thresholds_are_configurable() -> None:
    strict = DetectionSettings(max_ratio=Decimal("0.3"), min_saving=Decimal("100"))
    assert evaluate(Decimal("400"), Decimal("1000"), strict) is None
    assert evaluate(Decimal("250"), Decimal("1000"), strict) is not None
