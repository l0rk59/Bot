"""Extraction des offres depuis le HTML, à partir des données structurées (schema.org).

Ordre de préférence : JSON-LD (`Product`, `ItemList`, `ProductGroup`, `@graph`), puis les
balises OpenGraph `product:price:amount` en dernier recours sur une page produit.
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from urllib.parse import urldefrag, urljoin

from selectolax.lexbor import LexborHTMLParser

from pricebot.models import Availability, Condition, RawOffer
from pricebot.prices import parse_price

log = logging.getLogger(__name__)

_TRAILING_COMMAS = re.compile(r",\s*([}\]])")
_GTIN_KEYS = ("gtin13", "gtin14", "gtin12", "gtin8", "gtin", "ean")
_LIST_PRICE_TYPES = ("listprice", "strikethroughprice", "msrp")


@dataclass
class PageData:
    """Ce qu'une page contient : produits principaux et produits listés (page catégorie)."""

    products: list[RawOffer] = field(default_factory=list)
    listing: list[RawOffer] = field(default_factory=list)


def extract_page(html: str, page_url: str) -> PageData:
    """Lit toutes les offres d'une page (page produit ou page de liste)."""
    data = PageData()
    for block in iter_jsonld(html):
        for node in _top_level_nodes(block):
            if _is_type(node, "ItemList"):
                for item in _as_list(node.get("itemListElement")):
                    for product in _products_in(_list_item(item)):
                        offer = offer_from_product(product, page_url)
                        if offer is not None:
                            data.listing.append(offer)
            else:
                for product in _products_in(node):
                    offer = offer_from_product(product, page_url)
                    if offer is not None:
                        data.products.append(offer)
    if not data.products and not data.listing:
        og_offer = _offer_from_opengraph(html, page_url)
        if og_offer is not None:
            data.products.append(og_offer)
    return data


def extract_product(html: str, page_url: str) -> RawOffer | None:
    """Renvoie l'offre principale d'une page produit, ou None."""
    data = extract_page(html, page_url)
    if not data.products:
        return None
    wanted = normalize_url(page_url)
    for offer in data.products:
        if normalize_url(offer.url) == wanted:
            return offer
    return data.products[0]


def iter_jsonld(html: str) -> Iterator[Any]:
    """Parcourt les blocs `<script type="application/ld+json">` lisibles d'une page."""
    tree = LexborHTMLParser(html)
    for node in tree.css("script"):
        script_type = (node.attributes.get("type") or "").lower()
        if not script_type.startswith("application/ld+json"):
            continue
        raw = node.text(deep=True)
        if not raw or not raw.strip():
            continue
        data = _loads_lenient(raw)
        if data is None:
            log.debug("Bloc JSON-LD illisible ignoré")
            continue
        yield data


def offer_from_product(product: dict[str, Any], page_url: str) -> RawOffer | None:
    """Construit une offre à partir d'un nœud schema.org `Product`."""
    title = _text(product.get("name"))
    if not title:
        return None

    best: dict[str, Any] | None = None
    best_price: Decimal | None = None
    for offer in _iter_offers(product.get("offers")):
        price = _offer_price(offer)
        if price is not None and (best_price is None or price < best_price):
            best, best_price = offer, price
    if best is None or best_price is None:
        return None

    url = _text(product.get("url")) or _text(best.get("url")) or page_url
    currency = _currency(best)
    return RawOffer(
        url=normalize_url(urljoin(page_url, url)),
        title=title,
        price=best_price,
        currency=currency,
        list_price=_list_price(best),
        availability=_availability(best.get("availability")),
        condition=_condition(best.get("itemCondition") or product.get("itemCondition")),
        seller=_name(best.get("seller")),
        gtin=_first_gtin(product, best),
        mpn=_text(product.get("mpn")),
        sku=_text(product.get("sku")),
        brand=_name(product.get("brand")),
        image=_first_url(product.get("image"), page_url),
    )


def normalize_url(url: str) -> str:
    """Supprime l'ancre (#…) et les espaces autour de l'URL."""
    return urldefrag(url.strip())[0]


def is_valid_gtin(value: str) -> bool:
    """Vérifie la longueur et la clé de contrôle d'un GTIN/EAN (8, 12, 13 ou 14 chiffres)."""
    if not value.isdigit() or len(value) not in (8, 12, 13, 14):
        return False
    digits = [int(char) for char in value]
    check = digits.pop()
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits)))
    return (10 - total % 10) % 10 == check


# --- Parcours du JSON-LD -------------------------------------------------------------------


def _loads_lenient(raw: str) -> Any:
    text = raw.strip()
    for prefix, suffix in (("<!--", "-->"), ("//<![CDATA[", "//]]>"), ("<![CDATA[", "]]>")):
        if text.startswith(prefix) and text.endswith(suffix):
            text = text[len(prefix) : -len(suffix)].strip()
    for candidate in (text, _TRAILING_COMMAS.sub(r"\1", text)):
        try:
            return json.loads(candidate, strict=False)
        except ValueError:
            continue
    return None


def _top_level_nodes(data: Any) -> Iterator[dict[str, Any]]:
    if isinstance(data, list):
        for item in data:
            yield from _top_level_nodes(item)
    elif isinstance(data, dict):
        if "@graph" in data:
            yield from _top_level_nodes(data["@graph"])
        else:
            yield data


def _products_in(node: Any) -> Iterator[dict[str, Any]]:
    if not isinstance(node, dict):
        return
    if _is_type(node, "ProductGroup"):
        for variant in _as_list(node.get("hasVariant")):
            if isinstance(variant, dict):
                yield from _products_in(variant)
    elif _is_type(node, "Product"):
        yield node


def _list_item(item: Any) -> Any:
    if isinstance(item, dict) and _is_type(item, "ListItem") and "item" in item:
        return item["item"]
    return item


def _iter_offers(offers: Any) -> Iterator[dict[str, Any]]:
    for offer in _as_list(offers):
        if not isinstance(offer, dict):
            continue
        if _is_type(offer, "AggregateOffer"):
            # Une fourchette de prix (page catégorie, plusieurs vendeurs) ne suffit pas :
            # on ne garde que les offres détaillées qu'elle contient éventuellement.
            yield from _iter_offers(offer.get("offers"))
        else:
            yield offer


def _offer_price(offer: dict[str, Any]) -> Decimal | None:
    price = parse_price(offer.get("price"))
    if price is not None:
        return price
    for spec in _as_list(offer.get("priceSpecification")):
        if isinstance(spec, dict) and not _is_list_price_spec(spec):
            price = parse_price(spec.get("price"))
            if price is not None:
                return price
    return None


def _list_price(offer: dict[str, Any]) -> Decimal | None:
    for spec in _as_list(offer.get("priceSpecification")):
        if isinstance(spec, dict) and _is_list_price_spec(spec):
            return parse_price(spec.get("price"))
    return None


def _is_list_price_spec(spec: dict[str, Any]) -> bool:
    price_type = (_text(spec.get("priceType")) or "").lower()
    return any(kind in price_type for kind in _LIST_PRICE_TYPES)


def _currency(offer: dict[str, Any]) -> str:
    currency = _text(offer.get("priceCurrency"))
    if not currency:
        for spec in _as_list(offer.get("priceSpecification")):
            if isinstance(spec, dict):
                currency = _text(spec.get("priceCurrency"))
                if currency:
                    break
    currency = (currency or "EUR").strip().upper()
    return currency if re.fullmatch(r"[A-Z]{3}", currency) else "EUR"


def _availability(value: Any) -> Availability:
    text = (_text(value) or "").rsplit("/", 1)[-1].lower()
    if text in ("instock", "instoreonly", "onlineonly", "limitedavailability"):
        return Availability.IN_STOCK
    if text in ("outofstock", "soldout", "discontinued"):
        return Availability.OUT_OF_STOCK
    if text in ("preorder", "presale", "backorder"):
        return Availability.PREORDER
    return Availability.UNKNOWN


def _condition(value: Any) -> Condition:
    text = (_text(value) or "").rsplit("/", 1)[-1].lower()
    if text == "newcondition":
        return Condition.NEW
    if text == "refurbishedcondition":
        return Condition.REFURBISHED
    if text in ("usedcondition", "damagedcondition"):
        return Condition.USED
    return Condition.UNKNOWN


def _first_gtin(*nodes: dict[str, Any]) -> str | None:
    for node in nodes:
        for key in _GTIN_KEYS:
            value = _text(node.get(key))
            if value:
                digits = re.sub(r"\D", "", value)
                canonical = canonical_gtin(digits)
                if canonical is not None:
                    return canonical
    return None


def canonical_gtin(digits: str) -> str | None:
    """Forme unique d'un GTIN pour comparer les sites : EAN-13 si possible, sinon GTIN-14.

    Les zéros de tête ne changent pas la clé de contrôle : « 0711719577294 » (EAN-13),
    « 00711719577294 » (GTIN-14) et « 711719577294 » (UPC) désignent le même produit.
    """
    stripped = digits.lstrip("0")
    if not stripped:
        return None
    candidate = stripped.zfill(13) if len(stripped) <= 13 else stripped
    return candidate if is_valid_gtin(candidate) else None


def _offer_from_opengraph(html: str, page_url: str) -> RawOffer | None:
    tree = LexborHTMLParser(html)

    def meta(*names: str) -> str | None:
        for name in names:
            node = tree.css_first(f'meta[property="{name}"]') or tree.css_first(
                f'meta[name="{name}"]'
            )
            if node is not None and node.attributes.get("content"):
                return node.attributes["content"]
        return None

    price = parse_price(meta("product:price:amount", "og:price:amount"))
    title = _text(meta("og:title"))
    if price is None or not title:
        return None
    currency = (meta("product:price:currency", "og:price:currency") or "EUR").upper()
    url = meta("og:url") or page_url
    return RawOffer(
        url=normalize_url(urljoin(page_url, url)),
        title=title,
        price=price,
        currency=currency if re.fullmatch(r"[A-Z]{3}", currency) else "EUR",
        availability=_availability(meta("product:availability", "og:availability")),
        image=_first_url(meta("og:image"), page_url),
    )


# --- Petits utilitaires --------------------------------------------------------------------


def _is_type(node: dict[str, Any], wanted: str) -> bool:
    types = node.get("@type")
    for value in _as_list(types):
        if isinstance(value, str) and value.rsplit("/", 1)[-1] == wanted:
            return True
    return False


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _text(value: Any) -> str | None:
    if isinstance(value, list):
        value = next((v for v in value if isinstance(v, str | int | float)), None)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        value = str(value)
    if not isinstance(value, str):
        return None
    text = " ".join(html_lib.unescape(value).split())
    return text or None


def _name(value: Any) -> str | None:
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, dict):
        return _text(value.get("name"))
    return _text(value)


def _first_url(value: Any, page_url: str) -> str | None:
    for item in _as_list(value):
        candidate = (
            _text(item.get("url") or item.get("contentUrl"))
            if isinstance(item, dict)
            else _text(item)
        )
        if candidate:
            return urljoin(page_url, candidate)
    return None
