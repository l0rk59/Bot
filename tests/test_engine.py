"""Tests de bout en bout : faux magasin → collecte → détection → vérification → alerte."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx
import pytest
from conftest import FakeClock, FakeMonotonic

from pricebot.alerts import NotificationError
from pricebot.engine import Engine
from pricebot.fake_shop import FakeShop
from pricebot.http import PoliteClient
from pricebot.retailers import ListingConfig, RetailerConfig
from pricebot.storage import Storage

BASE = "http://127.0.0.1:8765"


@dataclass
class RecordingNotifier:
    messages: list[str] = field(default_factory=list)
    fail: bool = False

    async def send(self, text: str) -> None:
        if self.fail:
            raise NotificationError("Telegram injoignable")
        self.messages.append(text)


def make_retailer(**changes: object) -> RetailerConfig:
    config = RetailerConfig(
        id="fake-shop",
        name="Magasin test",
        base_url=BASE,
        min_interval_seconds=0,
        page_url_template="{url}page{page}/",
        listings=[ListingConfig(url=f"{BASE}/categorie/", max_pages=2)],
    )
    return config.model_copy(update=changes)


@dataclass
class Harness:
    shop: FakeShop
    engine: Engine
    storage: Storage
    notifier: RecordingNotifier
    clock: FakeClock


@pytest.fixture
async def harness(clock: FakeClock, monotonic: FakeMonotonic) -> AsyncIterator[Harness]:
    shop = FakeShop(BASE)
    storage = Storage(":memory:")
    notifier = RecordingNotifier()
    client = PoliteClient(
        "pricebot-test", transport=shop.mock_transport(), sleep=monotonic.sleep, clock=monotonic
    )
    engine = Engine([make_retailer()], storage, client, notifier, clock=clock)
    yield Harness(shop, engine, storage, notifier, clock)
    await client.aclose()
    storage.close()


async def test_first_pass_only_records_prices(harness: Harness) -> None:
    report = await harness.engine.run_cycle()

    assert report.pages == 1  # la page 2 est vide : fin de la catégorie
    assert report.offers == 4
    assert report.changes == 4
    assert report.alerts == 0
    assert report.errors == 0
    assert harness.notifier.messages == []


async def test_price_error_triggers_one_verified_alert_then_an_end_message(
    harness: Harness,
) -> None:
    await harness.engine.run_cycle()
    harness.clock.advance(hours=12)
    harness.shop.set_price(1, "129.90")  # 1 299 € → 129,90 € : virgule décalée

    report = await harness.engine.run_cycle()
    assert report.alerts == 1
    assert "/produit/1.html" in harness.shop.requests  # vérifié sur la fiche produit
    message = harness.notifier.messages[0]
    assert "Erreur de prix probable" in message
    assert "129,90" in message
    assert "virgule décalée (×10)" in message
    assert "-90 %" in message
    assert "EAN 2000000000015" in message  # détail lu sur la fiche produit
    assert "non vérifiée" not in message
    assert "Vendeur tiers" in message  # « Faux magasin » n'est pas déclaré comme vendeur maison

    harness.clock.advance(minutes=15)
    report = await harness.engine.run_cycle()
    assert report.alerts == 0  # pas de doublon tant que l'erreur dure
    assert len(harness.notifier.messages) == 1

    harness.clock.advance(minutes=40)
    harness.shop.set_price(1, "1299.00")
    report = await harness.engine.run_cycle()
    assert report.resolved == 1
    assert "Fin de l'erreur de prix" in harness.notifier.messages[-1]
    assert "55 min" in harness.notifier.messages[-1]


async def test_listing_glitch_is_rejected_by_the_product_page(harness: Harness) -> None:
    await harness.engine.run_cycle()
    harness.clock.advance(hours=1)
    harness.shop.set_price(2, "99.00", listing_only=True)  # seule la liste affiche 99 €

    report = await harness.engine.run_cycle()
    assert report.alerts == 0
    assert report.rejected == 1
    assert harness.notifier.messages == []
    assert harness.storage.counts()["anomalies_rejected"] == 1


async def test_out_of_stock_price_error_is_not_alerted(harness: Harness) -> None:
    await harness.engine.run_cycle()
    harness.clock.advance(hours=1)
    harness.shop.set_price(3, "89.90")
    harness.shop.set_stock(3, in_stock=False)

    report = await harness.engine.run_cycle()
    assert report.alerts == 0
    assert report.changes == 1


async def test_small_or_normal_drops_are_ignored(harness: Harness) -> None:
    await harness.engine.run_cycle()
    harness.clock.advance(hours=1)
    harness.shop.set_price(4, "249.00")  # -29 % : promotion classique
    harness.shop.set_price(1, "999.00")  # -23 %

    report = await harness.engine.run_cycle()
    assert report.changes == 2
    assert report.alerts == 0


async def test_a_deeper_drop_is_alerted_again(harness: Harness) -> None:
    await harness.engine.run_cycle()
    harness.clock.advance(hours=1)
    harness.shop.set_price(2, "400.00")
    await harness.engine.run_cycle()
    harness.clock.advance(minutes=15)
    harness.shop.set_price(2, "100.00")  # encore -75 % par rapport à l'alerte précédente

    report = await harness.engine.run_cycle()
    assert report.alerts == 1
    assert len(harness.notifier.messages) == 2


async def test_failed_alert_is_retried_on_next_pass(harness: Harness) -> None:
    await harness.engine.run_cycle()
    harness.clock.advance(hours=1)
    harness.shop.set_price(1, "12.99")
    harness.notifier.fail = True

    report = await harness.engine.run_cycle()
    assert report.alerts == 0
    assert report.errors == 1

    harness.notifier.fail = False
    harness.clock.advance(minutes=15)
    report = await harness.engine.run_cycle()
    assert report.alerts == 1
    assert "virgule décalée (×100)" in harness.notifier.messages[0]


async def test_own_seller_is_not_flagged(clock: FakeClock, monotonic: FakeMonotonic) -> None:
    shop = FakeShop(BASE)
    notifier = RecordingNotifier()
    retailer = make_retailer(own_seller_names=["Faux magasin"])
    async with PoliteClient(
        "t", transport=shop.mock_transport(), sleep=monotonic.sleep, clock=monotonic
    ) as client:
        engine = Engine([retailer], Storage(":memory:"), client, notifier, clock=clock)
        await engine.run_cycle()
        clock.advance(hours=1)
        shop.set_price(1, "129.90")
        await engine.run_cycle()
    assert len(notifier.messages) == 1
    assert "Vendeur tiers" not in notifier.messages[0]


async def test_watched_product_pages(clock: FakeClock, monotonic: FakeMonotonic) -> None:
    shop = FakeShop(BASE)
    notifier = RecordingNotifier()
    retailer = make_retailer(listings=[], products=[shop.product_url(3)])
    async with PoliteClient(
        "t", transport=shop.mock_transport(), sleep=monotonic.sleep, clock=monotonic
    ) as client:
        engine = Engine([retailer], Storage(":memory:"), client, notifier, clock=clock)
        report = await engine.run_cycle()
        assert report.offers == 1
        clock.advance(hours=1)
        shop.set_price(3, "89.90")
        report = await engine.run_cycle()
    assert report.alerts == 1
    assert shop.requests.count("/produit/3.html") == 2  # pas de double lecture pour vérifier


async def test_a_site_that_blocks_the_bot_is_left_alone(
    clock: FakeClock, monotonic: FakeMonotonic
) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(403, text="Accès refusé")

    async with PoliteClient(
        "t", transport=httpx.MockTransport(handler), sleep=monotonic.sleep, clock=monotonic
    ) as client:
        engine = Engine(
            [make_retailer()], Storage(":memory:"), client, RecordingNotifier(), clock=clock
        )
        report = await engine.run_cycle()
    assert report.errors == 1
    assert calls == ["/robots.txt", "/categorie/"]  # arrêt immédiat sur ce site


async def test_robots_txt_can_forbid_a_category(clock: FakeClock, monotonic: FakeMonotonic) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /categorie/\n")
        raise AssertionError("page interdite lue")

    async with PoliteClient(
        "t", transport=httpx.MockTransport(handler), sleep=monotonic.sleep, clock=monotonic
    ) as client:
        engine = Engine(
            [make_retailer()], Storage(":memory:"), client, RecordingNotifier(), clock=clock
        )
        report = await engine.run_cycle()
    assert report.pages == 0
    assert report.errors == 0


async def test_page_without_prices_is_reported(clock: FakeClock, monotonic: FakeMonotonic) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text="<html><body>Nouvelle maquette</body></html>")

    async with PoliteClient(
        "t", transport=httpx.MockTransport(handler), sleep=monotonic.sleep, clock=monotonic
    ) as client:
        engine = Engine(
            [make_retailer()], Storage(":memory:"), client, RecordingNotifier(), clock=clock
        )
        report = await engine.run_cycle()
    assert report.errors == 1
