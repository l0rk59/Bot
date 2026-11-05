"""Modèles de données communs."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Availability(StrEnum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    PREORDER = "preorder"
    UNKNOWN = "unknown"


class Condition(StrEnum):
    NEW = "new"
    REFURBISHED = "refurbished"
    USED = "used"
    UNKNOWN = "unknown"


class RawOffer(BaseModel):
    """Une offre telle que lue sur une page : un produit, chez un marchand, à un prix."""

    model_config = ConfigDict(frozen=True)

    url: str
    title: str
    price: Decimal
    currency: str = "EUR"
    list_price: Decimal | None = None
    availability: Availability = Availability.UNKNOWN
    condition: Condition = Condition.UNKNOWN
    seller: str | None = None
    gtin: str | None = None
    mpn: str | None = None
    sku: str | None = None
    brand: str | None = None
    image: str | None = None
