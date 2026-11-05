from datetime import timedelta
from decimal import Decimal

import pytest
from conftest import FakeClock

from pricebot.models import Availability, Condition, RawOffer
from pricebot.storage import AnomalyStatus, Storage


@pytest.fixture
def storage() -> Storage:
    return Storage(":memory:")


def offer(price: str, **changes: object) -> RawOffer:
    base = RawOffer(
        url="https://shop.example/p1",
        title="Produit 1",
        price=Decimal(price),
        availability=Availability.IN_STOCK,
    )
    return base.model_copy(update=changes)


def test_only_price_or_stock_changes_are_stored(storage: Storage, clock: FakeClock) -> None:
    stored = storage.upsert_offer("shop", offer("100"), clock.now)
    assert storage.record_observation(stored.id, offer("100"), "listing", clock.now)
    clock.advance(minutes=15)
    assert not storage.record_observation(stored.id, offer("100"), "listing", clock.now)
    clock.advance(minutes=15)
    assert storage.record_observation(stored.id, offer("90"), "listing", clock.now)
    clock.advance(minutes=15)
    out = offer("90", availability=Availability.OUT_OF_STOCK)
    assert storage.record_observation(stored.id, out, "listing", clock.now)

    assert storage.counts()["price_observations"] == 3
    refreshed = storage.get_offer(stored.id)
    assert refreshed is not None
    assert refreshed.last_price == Decimal("90")
    assert refreshed.availability is Availability.OUT_OF_STOCK


def test_history_starts_with_the_price_in_force(storage: Storage, clock: FakeClock) -> None:
    start = clock.now
    stored = storage.upsert_offer("shop", offer("100"), clock.now)
    storage.record_observation(stored.id, offer("100"), "listing", clock.now)
    clock.advance(days=40)
    storage.record_observation(stored.id, offer("80"), "listing", clock.now)

    since = clock.now - timedelta(days=30)
    history = storage.history(stored.id, since)
    assert [p.price for p in history] == [Decimal("100"), Decimal("80")]
    assert history[0].observed_at == since  # ramené au début de la fenêtre
    assert history[0].observed_at > start


def test_upsert_keeps_details_missing_from_listing_pages(
    storage: Storage, clock: FakeClock
) -> None:
    detailed = offer("100", gtin="3700527316901", seller="Boutique", condition=Condition.NEW)
    stored = storage.upsert_offer("shop", detailed, clock.now)
    storage.upsert_offer("shop", offer("95"), clock.now)  # page de liste : moins d'infos

    details = storage.offer_details(stored.id)
    assert details["gtin"] == "3700527316901"
    assert details["seller"] == "Boutique"
    assert details["condition"] == "new"


def test_anomaly_lifecycle(storage: Storage, clock: FakeClock) -> None:
    stored = storage.upsert_offer("shop", offer("10"), clock.now)
    assert storage.active_anomaly(stored.id) is None

    storage.add_anomaly(
        stored.id,
        clock.now,
        Decimal("10"),
        Decimal("100"),
        Decimal("0.1"),
        ["x"],
        AnomalyStatus.REJECTED,
    )
    assert storage.active_anomaly(stored.id) is None  # une fausse alerte n'est pas active

    anomaly_id = storage.add_anomaly(
        stored.id,
        clock.now,
        Decimal("10"),
        Decimal("100"),
        Decimal("0.1"),
        ["x"],
        AnomalyStatus.ALERTED,
    )
    active = storage.active_anomaly(stored.id)
    assert active is not None
    assert active.id == anomaly_id
    assert active.price == Decimal("10")

    storage.resolve_anomaly(anomaly_id, clock.now)
    assert storage.active_anomaly(stored.id) is None
    counts = storage.counts()
    assert counts["anomalies_resolved"] == 1
    assert counts["anomalies_rejected"] == 1


def test_naive_datetimes_are_refused(storage: Storage, clock: FakeClock) -> None:
    with pytest.raises(ValueError, match="UTC"):
        storage.upsert_offer("shop", offer("1"), clock.now.replace(tzinfo=None))


def test_database_file_is_created(tmp_path: object, clock: FakeClock) -> None:
    from pathlib import Path

    path = Path(str(tmp_path)) / "sous-dossier" / "pricebot.sqlite3"
    storage = Storage(path)
    storage.upsert_offer("shop", offer("1"), clock.now)
    storage.close()
    assert path.exists()
    reopened = Storage(path)
    assert reopened.counts()["offers"] == 1
    reopened.close()
