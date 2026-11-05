import json
from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest

from pricebot.alerts import (
    AlertContext,
    ConsoleNotifier,
    NotificationError,
    TelegramNotifier,
    format_alert,
    format_resolved,
)
from pricebot.detection import DetectionSettings, Verdict, evaluate
from pricebot.models import Availability, Condition, RawOffer

TOKEN = "123456:SECRET-TOKEN"


def sample_offer(**changes: object) -> RawOffer:
    offer = RawOffer(
        url="https://shop.example/p?a=1&b=2",
        title='TV <OLED> 55" & co',
        price=Decimal("129.90"),
        availability=Availability.IN_STOCK,
        condition=Condition.NEW,
        seller="Boutique",
        gtin="3700527316901",
    )
    return offer.model_copy(update=changes)


def sample_verdict() -> Verdict:
    verdict = evaluate(Decimal("129.90"), Decimal("1299"), DetectionSettings())
    assert verdict is not None
    return verdict


def test_alert_message_is_escaped_and_complete() -> None:
    context = AlertContext("Boutique", third_party_seller=False, verified=True)
    message = format_alert(sample_offer(), sample_verdict(), context)

    assert "TV &lt;OLED&gt; 55&quot; &amp; co" in message
    assert 'href="https://shop.example/p?a=1&amp;b=2"' in message
    assert "129,90" in message
    assert "-90 %" in message
    assert "En stock · Neuf" in message
    assert "EAN 3700527316901" in message
    assert "Vendeur tiers" not in message
    assert "non vérifiée" not in message


def test_alert_warnings() -> None:
    context = AlertContext("Boutique", third_party_seller=True, verified=False)
    offer = sample_offer(condition=Condition.REFURBISHED)
    message = format_alert(offer, sample_verdict(), context)
    assert "Vendeur tiers" in message
    assert "reconditionné" in message
    assert "non vérifiée" in message


def test_resolved_message() -> None:
    message = format_resolved("TV", "https://x", Decimal("1299"), "EUR", timedelta(hours=2))
    assert "2 h" in message
    assert "1 299,00" in message
    assert "3 jours" in format_resolved("TV", "https://x", Decimal(1), "EUR", timedelta(days=3))


async def test_console_notifier_prints_plain_text(capsys: pytest.CaptureFixture[str]) -> None:
    await ConsoleNotifier().send("<b>Bonjour</b> &amp; bienvenue")
    assert "Bonjour & bienvenue" in capsys.readouterr().out


def telegram(handler: Callable[[httpx.Request], httpx.Response]) -> TelegramNotifier:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TelegramNotifier(TOKEN, "-100123", client=client)


async def test_telegram_send() -> None:
    sent: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/bot{TOKEN}/sendMessage"
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {}})

    await telegram(handler).send("<b>Alerte</b>")
    assert sent[0]["chat_id"] == "-100123"
    assert sent[0]["parse_mode"] == "HTML"
    assert sent[0]["text"] == "<b>Alerte</b>"


async def test_telegram_refusal_is_reported() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400, json={"ok": False, "error_code": 400, "description": "chat not found"}
        )

    with pytest.raises(NotificationError, match="chat not found"):
        await telegram(handler).send("x")


async def test_telegram_errors_never_reveal_the_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(NotificationError) as error:
        await telegram(handler).send("x")
    assert TOKEN not in str(error.value)
    assert error.value.__cause__ is None


async def test_telegram_rate_limit_is_retried() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                429,
                json={"ok": False, "error_code": 429, "parameters": {"retry_after": 0.01}},
            )
        return httpx.Response(200, json={"ok": True})

    await telegram(handler).send("x")
    assert calls["n"] == 2


async def test_telegram_find_chats() -> None:
    updates = {
        "ok": True,
        "result": [
            {
                "my_chat_member": {
                    "chat": {"id": -100123, "title": "Erreurs de prix", "type": "supergroup"}
                }
            },
            {"message": {"chat": {"id": 42, "first_name": "Moi", "type": "private"}}},
            {
                "message": {
                    "chat": {"id": -100123, "title": "Erreurs de prix", "type": "supergroup"}
                }
            },
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=updates)

    chats = await telegram(handler).find_chats()
    assert chats == [("-100123", "Erreurs de prix (supergroup)"), ("42", "Moi (private)")]
