"""Détection des prix anormalement bas (version MVP, voir docs/DETECTION.md)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from pricebot.prices import format_price, percent_drop
from pricebot.storage import PricePoint

DECIMAL_SHIFT_FACTORS = (10, 100, 1000)


@dataclass(frozen=True)
class DetectionSettings:
    max_ratio: Decimal = Decimal("0.5")  # alerte si prix <= 50 % du prix habituel
    min_saving: Decimal = Decimal("30")  # économie minimale en euros
    shift_tolerance: Decimal = Decimal("0.10")  # ±10 % pour la virgule décalée
    window: timedelta = timedelta(days=30)  # fenêtre de l'historique
    realert_drop: Decimal = Decimal("0.2")  # nouvelle alerte si le prix baisse encore de 20 %


@dataclass(frozen=True)
class Verdict:
    """Un prix jugé anormal, avec ses raisons."""

    price: Decimal
    reference: Decimal
    ratio: Decimal
    saving: Decimal
    reasons: tuple[str, ...]


def time_weighted_median(points: Sequence[PricePoint], now: datetime) -> Decimal | None:
    """Médiane des prix, chaque prix pesant la durée pendant laquelle il a été affiché.

    Une promotion de 2 heures pèse donc peu face à un prix stable pendant 3 semaines.
    """
    if not points:
        return None
    weighted: list[tuple[Decimal, float]] = []
    for index, point in enumerate(points):
        end = points[index + 1].observed_at if index + 1 < len(points) else now
        seconds = max((end - point.observed_at).total_seconds(), 1.0)
        weighted.append((point.price, seconds))
    weighted.sort(key=lambda item: item[0])
    half = sum(weight for _, weight in weighted) / 2
    cumulated = 0.0
    for price, weight in weighted:
        cumulated += weight
        if cumulated >= half:
            return price
    return weighted[-1][0]


def decimal_shift(price: Decimal, reference: Decimal, tolerance: Decimal) -> int | None:
    """Renvoie 10, 100 ou 1000 si le prix ressemble au prix habituel avec la virgule décalée."""
    if price <= 0 or reference <= 0:
        return None
    for factor in DECIMAL_SHIFT_FACTORS:
        if abs(price * factor - reference) <= reference * tolerance:
            return factor
    return None


def evaluate(
    price: Decimal, reference: Decimal | None, settings: DetectionSettings, currency: str = "EUR"
) -> Verdict | None:
    """Juge un prix par rapport au prix habituel. None si le prix n'a rien d'anormal."""
    if reference is None or reference <= 0:
        return None
    ratio = price / reference
    saving = reference - price
    if saving < settings.min_saving:
        return None

    reasons: list[str] = []
    factor = decimal_shift(price, reference, settings.shift_tolerance)
    if factor is not None:
        reasons.append(f"virgule décalée (×{factor})")
    if price <= Decimal(1) and reference >= Decimal(50):
        reasons.append("prix symbolique")
    if ratio <= settings.max_ratio:
        reasons.append(
            f"-{percent_drop(price, reference)} % par rapport au prix habituel "
            f"({format_price(reference, currency)})"
        )
    if not reasons:
        return None
    return Verdict(
        price=price, reference=reference, ratio=ratio, saving=saving, reasons=tuple(reasons)
    )
