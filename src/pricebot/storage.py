"""Stockage SQLite : offres, historique des prix (seulement les changements) et anomalies."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from pricebot.models import Availability, RawOffer

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY,
    retailer TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    gtin TEXT,
    brand TEXT,
    mpn TEXT,
    sku TEXT,
    seller TEXT,
    condition TEXT,
    currency TEXT NOT NULL,
    last_price TEXT,
    availability TEXT,
    first_seen_at TEXT NOT NULL,
    last_checked_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS offers_gtin ON offers (gtin);
CREATE TABLE IF NOT EXISTS price_observations (
    id INTEGER PRIMARY KEY,
    offer_id INTEGER NOT NULL REFERENCES offers (id),
    observed_at TEXT NOT NULL,
    price TEXT NOT NULL,
    list_price TEXT,
    currency TEXT NOT NULL,
    availability TEXT NOT NULL,
    source TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS observations_offer_time ON price_observations (offer_id, observed_at);
CREATE TABLE IF NOT EXISTS anomalies (
    id INTEGER PRIMARY KEY,
    offer_id INTEGER NOT NULL REFERENCES offers (id),
    detected_at TEXT NOT NULL,
    price TEXT NOT NULL,
    reference_price TEXT NOT NULL,
    ratio TEXT NOT NULL,
    reasons TEXT NOT NULL,
    status TEXT NOT NULL,
    note TEXT,
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS anomalies_offer_status ON anomalies (offer_id, status);
"""


@dataclass(frozen=True)
class PricePoint:
    observed_at: datetime
    price: Decimal
    availability: Availability


@dataclass(frozen=True)
class StoredOffer:
    id: int
    retailer: str
    url: str
    title: str
    last_price: Decimal | None
    availability: Availability | None


@dataclass(frozen=True)
class Anomaly:
    id: int
    offer_id: int
    detected_at: datetime
    price: Decimal
    reference_price: Decimal
    status: str


class AnomalyStatus:
    ALERTED = "alerted"  # alerte envoyée, erreur en cours
    REJECTED = "rejected"  # écartée par la vérification
    FAILED = "failed"  # alerte non envoyée (réessayée au passage suivant)
    RESOLVED = "resolved"  # le prix est revenu à la normale


class Storage:
    """Accès à la base SQLite. Utilisé depuis une seule boucle asyncio."""

    def __init__(self, path: Path | str) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        if str(path) != ":memory:":
            self._db.execute("PRAGMA journal_mode = WAL")
        with self._db:
            self._db.executescript(SCHEMA)
            self._db.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    def close(self) -> None:
        self._db.close()

    # --- Offres --------------------------------------------------------------------------

    def upsert_offer(self, retailer: str, offer: RawOffer, now: datetime) -> StoredOffer:
        """Crée l'offre si besoin et met à jour ses informations descriptives."""
        with self._db:
            self._db.execute(
                """
                INSERT INTO offers (retailer, url, title, gtin, brand, mpn, sku, seller,
                                    condition, currency, first_seen_at, last_checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (url) DO UPDATE SET
                    title = excluded.title,
                    gtin = COALESCE(excluded.gtin, offers.gtin),
                    brand = COALESCE(excluded.brand, offers.brand),
                    mpn = COALESCE(excluded.mpn, offers.mpn),
                    sku = COALESCE(excluded.sku, offers.sku),
                    seller = COALESCE(excluded.seller, offers.seller),
                    condition = CASE WHEN excluded.condition = 'unknown'
                                     THEN offers.condition ELSE excluded.condition END
                """,
                (
                    retailer,
                    offer.url,
                    offer.title,
                    offer.gtin,
                    offer.brand,
                    offer.mpn,
                    offer.sku,
                    offer.seller,
                    offer.condition.value,
                    offer.currency,
                    _ts(now),
                    _ts(now),
                ),
            )
        row = self._db.execute("SELECT * FROM offers WHERE url = ?", (offer.url,)).fetchone()
        return _stored_offer(row)

    def get_offer(self, offer_id: int) -> StoredOffer | None:
        row = self._db.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)).fetchone()
        return _stored_offer(row) if row else None

    def offer_details(self, offer_id: int) -> dict[str, str | None]:
        row = self._db.execute(
            "SELECT seller, condition, gtin, brand FROM offers WHERE id = ?", (offer_id,)
        ).fetchone()
        return dict(row) if row else {}

    # --- Historique ----------------------------------------------------------------------

    def record_observation(
        self, offer_id: int, offer: RawOffer, source: str, now: datetime
    ) -> bool:
        """Enregistre le prix vu. Ne crée une ligne que si le prix ou le stock a changé."""
        last = self._db.execute(
            """
            SELECT price, availability FROM price_observations
            WHERE offer_id = ? ORDER BY observed_at DESC, id DESC LIMIT 1
            """,
            (offer_id,),
        ).fetchone()
        changed = (
            last is None
            or Decimal(last["price"]) != offer.price
            or last["availability"] != offer.availability.value
        )
        with self._db:
            if changed:
                self._db.execute(
                    """
                    INSERT INTO price_observations
                        (offer_id, observed_at, price, list_price, currency, availability, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        offer_id,
                        _ts(now),
                        str(offer.price),
                        str(offer.list_price) if offer.list_price is not None else None,
                        offer.currency,
                        offer.availability.value,
                        source,
                    ),
                )
            self._db.execute(
                """
                UPDATE offers SET last_checked_at = ?, last_price = ?, availability = ?,
                                  currency = ?
                WHERE id = ?
                """,
                (_ts(now), str(offer.price), offer.availability.value, offer.currency, offer_id),
            )
        return changed

    def history(self, offer_id: int, since: datetime) -> list[PricePoint]:
        """Prix observés depuis `since`, précédés du prix en vigueur à cette date."""
        before = self._db.execute(
            """
            SELECT observed_at, price, availability FROM price_observations
            WHERE offer_id = ? AND observed_at < ?
            ORDER BY observed_at DESC, id DESC LIMIT 1
            """,
            (offer_id, _ts(since)),
        ).fetchone()
        rows = self._db.execute(
            """
            SELECT observed_at, price, availability FROM price_observations
            WHERE offer_id = ? AND observed_at >= ?
            ORDER BY observed_at, id
            """,
            (offer_id, _ts(since)),
        ).fetchall()
        points = [_price_point(row) for row in rows]
        if before is not None:
            start = _price_point(before)
            points.insert(0, PricePoint(since, start.price, start.availability))
        return points

    # --- Anomalies -----------------------------------------------------------------------

    def add_anomaly(
        self,
        offer_id: int,
        now: datetime,
        price: Decimal,
        reference: Decimal,
        ratio: Decimal,
        reasons: Sequence[str],
        status: str,
        note: str | None = None,
    ) -> int:
        with self._db:
            cursor = self._db.execute(
                """
                INSERT INTO anomalies
                    (offer_id, detected_at, price, reference_price, ratio, reasons, status, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    offer_id,
                    _ts(now),
                    str(price),
                    str(reference),
                    str(ratio),
                    json.dumps(list(reasons), ensure_ascii=False),
                    status,
                    note,
                ),
            )
        return int(cursor.lastrowid or 0)

    def active_anomaly(self, offer_id: int) -> Anomaly | None:
        """Dernière anomalie signalée et pas encore résolue pour cette offre."""
        row = self._db.execute(
            """
            SELECT * FROM anomalies WHERE offer_id = ? AND status = ?
            ORDER BY detected_at DESC, id DESC LIMIT 1
            """,
            (offer_id, AnomalyStatus.ALERTED),
        ).fetchone()
        if row is None:
            return None
        return Anomaly(
            id=row["id"],
            offer_id=row["offer_id"],
            detected_at=_parse_ts(row["detected_at"]),
            price=Decimal(row["price"]),
            reference_price=Decimal(row["reference_price"]),
            status=row["status"],
        )

    def resolve_anomaly(self, anomaly_id: int, now: datetime) -> None:
        with self._db:
            self._db.execute(
                "UPDATE anomalies SET status = ?, resolved_at = ? WHERE id = ?",
                (AnomalyStatus.RESOLVED, _ts(now), anomaly_id),
            )

    # --- Statistiques --------------------------------------------------------------------

    def counts(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for table in ("offers", "price_observations"):
            result[table] = self._db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for row in self._db.execute("SELECT status, COUNT(*) AS n FROM anomalies GROUP BY status"):
            result[f"anomalies_{row['status']}"] = row["n"]
        retailers = self._db.execute(
            "SELECT retailer, COUNT(*) AS n FROM offers GROUP BY retailer ORDER BY retailer"
        )
        for row in retailers:
            result[f"offers_{row['retailer']}"] = row["n"]
        return result


def _ts(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("Les dates doivent être en UTC avec fuseau horaire")
    return moment.astimezone(UTC).isoformat(timespec="microseconds")


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _price_point(row: sqlite3.Row) -> PricePoint:
    return PricePoint(
        observed_at=_parse_ts(row["observed_at"]),
        price=Decimal(row["price"]),
        availability=Availability(row["availability"]),
    )


def _stored_offer(row: sqlite3.Row) -> StoredOffer:
    return StoredOffer(
        id=row["id"],
        retailer=row["retailer"],
        url=row["url"],
        title=row["title"],
        last_price=Decimal(row["last_price"]) if row["last_price"] is not None else None,
        availability=Availability(row["availability"]) if row["availability"] else None,
    )
