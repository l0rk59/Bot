"""Envoi des alertes : Telegram, ou la console si Telegram n'est pas configuré."""

from __future__ import annotations

import asyncio
import html
import logging
import re
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any, Protocol

import httpx

from pricebot.detection import Verdict
from pricebot.models import Availability, Condition, RawOffer
from pricebot.prices import format_price, percent_drop

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_MAX_LENGTH = 4096

_AVAILABILITY_LABELS = {
    Availability.IN_STOCK: "En stock",
    Availability.OUT_OF_STOCK: "Rupture de stock",
    Availability.PREORDER: "Précommande",
    Availability.UNKNOWN: "Stock inconnu",
}
_CONDITION_LABELS = {
    Condition.NEW: "Neuf",
    Condition.REFURBISHED: "Reconditionné",
    Condition.USED: "Occasion",
}


class NotificationError(Exception):
    """L'alerte n'a pas pu être envoyée."""


class Notifier(Protocol):
    async def send(self, text: str) -> None: ...


@dataclass(frozen=True)
class AlertContext:
    retailer_name: str
    third_party_seller: bool
    verified: bool


def format_alert(offer: RawOffer, verdict: Verdict, context: AlertContext) -> str:
    """Message d'alerte au format HTML de Telegram."""
    e = html.escape
    price = format_price(verdict.price, offer.currency)
    reference = format_price(verdict.reference, offer.currency)
    drop = percent_drop(verdict.price, verdict.reference)
    lines = [
        "🚨 <b>Erreur de prix probable</b>",
        f"<b>{e(offer.title)}</b>",
        f"💶 <b>{price}</b> au lieu d'environ {reference} (-{drop} %)",
        "🔎 " + " · ".join(e(reason) for reason in verdict.reasons),
    ]
    details = [e(context.retailer_name)]
    if offer.seller:
        details.append(f"vendu par {e(offer.seller)}")
    details.append(_AVAILABILITY_LABELS[offer.availability])
    if offer.condition in _CONDITION_LABELS:
        details.append(_CONDITION_LABELS[offer.condition])
    lines.append("🏪 " + " · ".join(details))
    if context.third_party_seller:
        lines.append("⚠️ Vendeur tiers : vérifiez sa fiabilité avant d'acheter.")
    if offer.condition in (Condition.REFURBISHED, Condition.USED):
        lines.append("⚠️ Produit reconditionné ou d'occasion.")
    if not context.verified:
        lines.append("⚠️ Prix lu sur la page de liste, fiche produit non vérifiée.")
    if offer.gtin:
        lines.append(f"🏷️ EAN {e(offer.gtin)}")
    lines.append(f'🔗 <a href="{e(offer.url, quote=True)}">Voir l\'offre</a>')
    lines.append("<i>Le marchand peut annuler une commande passée sur une erreur manifeste.</i>")
    return "\n".join(lines)


def format_resolved(
    title: str, url: str, price: Decimal, currency: str, duration: timedelta
) -> str:
    """Message de fin d'erreur : le prix est revenu à la normale ou le produit n'est plus dispo."""
    e = html.escape
    return (
        f"✅ <b>Fin de l'erreur de prix</b> après {_human_duration(duration)}\n"
        f'<a href="{e(url, quote=True)}">{e(title)}</a> : {format_price(price, currency)}'
    )


def _human_duration(duration: timedelta) -> str:
    minutes = max(1, round(duration.total_seconds() / 60))
    if minutes < 60:
        return f"{minutes} min"
    hours, rest = divmod(minutes, 60)
    if hours < 48:
        return f"{hours} h {rest:02d}" if rest else f"{hours} h"
    return f"{hours // 24} jours"


class ConsoleNotifier:
    """Affiche les alertes dans le terminal (quand Telegram n'est pas configuré)."""

    async def send(self, text: str) -> None:
        plain = html.unescape(re.sub(r"<[^>]+>", "", text))
        print(f"\n{'=' * 60}\n{plain}\n{'=' * 60}\n", flush=True)


class TelegramNotifier:
    """Envoie les alertes dans une conversation Telegram via l'API des bots."""

    def __init__(
        self, token: str, chat_id: str, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._token = token
        self._chat_id = chat_id
        self._client = client or httpx.AsyncClient(timeout=20.0)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def send(self, text: str) -> None:
        payload = {
            "chat_id": self._chat_id,
            "text": text[:TELEGRAM_MAX_LENGTH],
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": False},
        }
        for _attempt in range(3):
            data = await self._call("sendMessage", payload)
            if data.get("ok"):
                return
            retry_after = (data.get("parameters") or {}).get("retry_after")
            if data.get("error_code") == 429 and retry_after:
                await asyncio.sleep(float(retry_after))
                continue
            raise NotificationError(f"Telegram a refusé le message : {data.get('description')}")
        raise NotificationError("Telegram : trop de messages, réessayez plus tard")

    async def bot_name(self) -> str:
        data = await self._call("getMe", {})
        if not data.get("ok"):
            raise NotificationError(f"Jeton refusé par Telegram : {data.get('description')}")
        result = data.get("result") or {}
        return f"{result.get('first_name', '?')} (@{result.get('username', '?')})"

    async def find_chats(self) -> list[tuple[str, str]]:
        """Conversations où le bot a reçu un message ou a été ajouté : (identifiant, nom)."""
        data = await self._call("getUpdates", {"allowed_updates": []})
        if not data.get("ok"):
            raise NotificationError(f"Telegram : {data.get('description')}")
        chats: dict[str, str] = {}
        for update in data.get("result") or []:
            for key in ("message", "channel_post", "my_chat_member", "edited_message"):
                chat = (update.get(key) or {}).get("chat")
                if chat and "id" in chat:
                    name = chat.get("title") or chat.get("username") or chat.get("first_name")
                    chats[str(chat["id"])] = f"{name} ({chat.get('type', '?')})"
        return sorted(chats.items())

    async def _call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{TELEGRAM_API}/bot{self._token}/{method}"
        try:
            response = await self._client.post(url, json=payload)
        except httpx.HTTPError as error:
            # Ne jamais afficher l'URL : elle contient le jeton secret.
            raise NotificationError(f"Telegram injoignable ({type(error).__name__})") from None
        try:
            data = response.json()
        except ValueError:
            raise NotificationError(
                f"Réponse Telegram illisible (HTTP {response.status_code})"
            ) from None
        if not isinstance(data, dict):
            raise NotificationError("Réponse Telegram inattendue")
        return data
