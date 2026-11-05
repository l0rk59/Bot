"""Moteur : un passage complet sur les sites, de la collecte jusqu'à l'alerte."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pricebot.alerts import (
    AlertContext,
    NotificationError,
    Notifier,
    format_alert,
    format_resolved,
)
from pricebot.detection import DetectionSettings, Verdict, evaluate, time_weighted_median
from pricebot.extract import extract_page, extract_product
from pricebot.http import Blocked, FetchError, PoliteClient, RobotsDisallowed
from pricebot.models import Availability, RawOffer
from pricebot.prices import format_price
from pricebot.retailers import ListingConfig, RetailerConfig
from pricebot.storage import Anomaly, AnomalyStatus, Storage

log = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class CycleReport:
    pages: int = 0
    offers: int = 0
    changes: int = 0
    candidates: int = 0
    alerts: int = 0
    rejected: int = 0
    resolved: int = 0
    errors: int = 0

    def summary(self) -> str:
        return (
            f"{self.pages} pages, {self.offers} offres lues, {self.changes} changements de prix, "
            f"{self.alerts} alertes, {self.rejected} fausses alertes écartées, "
            f"{self.resolved} erreurs terminées, {self.errors} erreurs de collecte"
        )


class Engine:
    def __init__(
        self,
        retailers: list[RetailerConfig],
        storage: Storage,
        client: PoliteClient,
        notifier: Notifier,
        detection: DetectionSettings | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._retailers = retailers
        self._storage = storage
        self._client = client
        self._notifier = notifier
        self._detection = detection or DetectionSettings()
        self._clock = clock

    async def run_forever(
        self,
        interval: timedelta,
        after_cycle: Callable[[CycleReport], Awaitable[None]] | None = None,
    ) -> None:
        """Enchaîne les passages, en attendant `interval` entre deux débuts de passage."""
        while True:
            started = time.monotonic()
            report = await self.run_cycle()
            log.info("Passage terminé : %s", report.summary())
            if after_cycle is not None:
                await after_cycle(report)
            wait = max(0.0, interval.total_seconds() - (time.monotonic() - started))
            log.info("Prochain passage dans %.0f s", wait)
            await asyncio.sleep(wait)

    async def run_cycle(self) -> CycleReport:
        """Un passage sur tous les sites (en parallèle, chaque site à son propre rythme)."""
        report = CycleReport()
        results = await asyncio.gather(
            *(self._run_retailer(retailer, report) for retailer in self._retailers),
            return_exceptions=True,
        )
        for retailer, result in zip(self._retailers, results, strict=True):
            if isinstance(result, Exception):
                report.errors += 1
                log.error("Erreur inattendue sur %s", retailer.name, exc_info=result)
        return report

    # --- Collecte ------------------------------------------------------------------------

    async def _run_retailer(self, retailer: RetailerConfig, report: CycleReport) -> None:
        try:
            for listing in retailer.listings:
                await self._scan_listing(retailer, listing, report)
            for url in retailer.products:
                await self._scan_product(retailer, url, report)
        except Blocked as error:
            report.errors += 1
            log.warning(
                "%s refuse l'accès au robot (%s) : site ignoré pour ce passage",
                retailer.name,
                error,
            )

    async def _scan_listing(
        self, retailer: RetailerConfig, listing: ListingConfig, report: CycleReport
    ) -> None:
        for page in range(1, listing.max_pages + 1):
            url = retailer.page_url(listing.url, page)
            if url is None:
                return
            html = await self._get(retailer, url, report)
            if html is None:
                return
            data = extract_page(html, url)
            offers = data.listing or data.products
            if not offers:
                if page == 1:
                    report.errors += 1
                    log.warning("Aucun prix lu sur %s (structure de page modifiée ?)", url)
                return
            report.pages += 1
            for offer in offers:
                await self._process(retailer, offer, "listing", report)

    async def _scan_product(self, retailer: RetailerConfig, url: str, report: CycleReport) -> None:
        html = await self._get(retailer, url, report)
        if html is None:
            return
        offer = extract_product(html, url)
        if offer is None:
            report.errors += 1
            log.warning("Aucun prix lu sur %s (structure de page modifiée ?)", url)
            return
        report.pages += 1
        await self._process(retailer, offer.model_copy(update={"url": url}), "product", report)

    async def _get(self, retailer: RetailerConfig, url: str, report: CycleReport) -> str | None:
        try:
            return await self._client.get_text(url, min_interval=retailer.min_interval_seconds)
        except Blocked:
            raise
        except RobotsDisallowed:
            log.info("%s : interdit par robots.txt, page ignorée", url)
        except FetchError as error:
            report.errors += 1
            log.warning("%s", error)
        return None

    # --- Détection -----------------------------------------------------------------------

    async def _process(
        self, retailer: RetailerConfig, offer: RawOffer, source: str, report: CycleReport
    ) -> None:
        now = self._clock()
        stored = self._storage.upsert_offer(retailer.id, offer, now)
        # Le prix habituel est calculé AVANT d'enregistrer le nouveau prix.
        history = self._storage.history(stored.id, since=now - self._detection.window)
        reference = time_weighted_median(history, now)
        if self._storage.record_observation(stored.id, offer, source, now):
            report.changes += 1
        report.offers += 1

        verdict = None
        if offer.availability != Availability.OUT_OF_STOCK:
            verdict = evaluate(offer.price, reference, self._detection, offer.currency)
        active = self._storage.active_anomaly(stored.id)

        if verdict is None:
            if active is not None:
                await self._resolve(active, offer, now, report)
            return
        if active is not None and offer.price >= active.price * (1 - self._detection.realert_drop):
            return  # erreur déjà signalée, pas de nouvelle alerte
        report.candidates += 1
        await self._confirm_and_alert(retailer, stored.id, offer, source, verdict, active, report)

    async def _confirm_and_alert(
        self,
        retailer: RetailerConfig,
        offer_id: int,
        offer: RawOffer,
        source: str,
        verdict: Verdict,
        active: Anomaly | None,
        report: CycleReport,
    ) -> None:
        verified = source == "product"
        if not verified:
            # Vérification sur la fiche produit : le prix de la liste peut être faux ou périmé.
            html = await self._get(retailer, offer.url, report)
            product = extract_product(html, offer.url) if html else None
            if product is not None:
                verified = True
                product = product.model_copy(update={"url": offer.url})
                self._storage.upsert_offer(retailer.id, product, self._clock())
                confirmed = None
                if product.availability != Availability.OUT_OF_STOCK:
                    confirmed = evaluate(
                        product.price, verdict.reference, self._detection, product.currency
                    )
                if confirmed is None:
                    report.rejected += 1
                    note = (
                        f"fiche produit : {format_price(product.price, product.currency)}, "
                        f"{product.availability.value}"
                    )
                    self._record(offer_id, verdict, AnomalyStatus.REJECTED, note)
                    log.info("Fausse alerte écartée pour %s (%s)", offer.url, note)
                    return
                offer, verdict = product, confirmed

        context = AlertContext(
            retailer_name=retailer.name,
            third_party_seller=not retailer.is_own_seller(offer.seller),
            verified=verified,
        )
        try:
            await self._notifier.send(format_alert(offer, verdict, context))
        except NotificationError as error:
            report.errors += 1
            self._record(offer_id, verdict, AnomalyStatus.FAILED, str(error))
            log.error("Alerte non envoyée (nouvel essai au prochain passage) : %s", error)
            return
        if active is not None:
            self._storage.resolve_anomaly(active.id, self._clock())
        self._record(offer_id, verdict, AnomalyStatus.ALERTED)
        report.alerts += 1
        log.warning(
            "ALERTE : %s à %s au lieu d'environ %s (%s)",
            offer.title,
            format_price(verdict.price, offer.currency),
            format_price(verdict.reference, offer.currency),
            offer.url,
        )

    async def _resolve(
        self, active: Anomaly, offer: RawOffer, now: datetime, report: CycleReport
    ) -> None:
        self._storage.resolve_anomaly(active.id, now)
        report.resolved += 1
        log.info("Fin de l'erreur de prix : %s", offer.url)
        text = format_resolved(
            offer.title, offer.url, offer.price, offer.currency, now - active.detected_at
        )
        if offer.availability == Availability.OUT_OF_STOCK:
            text += " (rupture de stock)"
        try:
            await self._notifier.send(text)
        except NotificationError as error:
            log.error("Message de fin d'erreur non envoyé : %s", error)

    def _record(
        self, offer_id: int, verdict: Verdict, status: str, note: str | None = None
    ) -> None:
        self._storage.add_anomaly(
            offer_id,
            self._clock(),
            verdict.price,
            verdict.reference,
            verdict.ratio,
            verdict.reasons,
            status,
            note,
        )
