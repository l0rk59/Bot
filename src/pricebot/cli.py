"""Ligne de commande : pricebot run | check | telegram-test | stats | fake-shop."""

from __future__ import annotations

import argparse
import asyncio
import io
import logging
import sys
from collections.abc import Awaitable, Callable, Coroutine
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from pricebot import __version__
from pricebot.alerts import ConsoleNotifier, NotificationError, Notifier, TelegramNotifier
from pricebot.engine import CycleReport, Engine
from pricebot.extract import extract_page
from pricebot.fake_shop import FakeShop, serve
from pricebot.http import FetchError, PoliteClient
from pricebot.models import RawOffer
from pricebot.prices import format_price
from pricebot.retailers import ConfigError, load_retailers, select_retailers
from pricebot.settings import Settings
from pricebot.storage import Storage

log = logging.getLogger("pricebot")

Command = Callable[[Settings, argparse.Namespace], Coroutine[None, None, int]]


def main(argv: list[str] | None = None) -> int:
    _fix_console_encoding()
    args = _build_parser().parse_args(argv)
    try:
        settings = Settings()
    except ValidationError as error:
        print(f"Réglage invalide dans le fichier .env :\n{error}", file=sys.stderr)
        return 2
    _configure_logging(args.verbose, settings.db_path.parent if args.command == "run" else None)
    try:
        if args.command == "fake-shop":
            serve(FakeShop(base_url=f"http://127.0.0.1:{args.port}"), port=args.port)
            return 0
        command: Command = _COMMANDS[args.command]
        return asyncio.run(command(settings, args))
    except ConfigError as error:
        print(f"Erreur de configuration : {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nArrêt demandé.")
        return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pricebot", description="Bot personnel de détection d'erreurs de prix."
    )
    parser.add_argument("--version", action="version", version=f"pricebot {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="journal détaillé")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMANDE")

    run = sub.add_parser("run", help="lancer la surveillance des prix")
    run.add_argument("--once", action="store_true", help="un seul passage, puis arrêt")
    run.add_argument(
        "--only",
        action="append",
        metavar="SITE",
        help="surveiller seulement ce site (identifiant du fichier YAML, option répétable)",
    )
    run.add_argument(
        "--interval",
        type=float,
        metavar="MINUTES",
        help="minutes entre deux passages (par défaut : réglage du fichier .env)",
    )

    check = sub.add_parser("check", help="lire une page et afficher les prix trouvés")
    check.add_argument("url")
    check.add_argument("--limit", type=int, default=10, help="produits affichés pour une liste")

    sub.add_parser("telegram-test", help="vérifier la configuration Telegram")
    sub.add_parser("stats", help="afficher le contenu de la base")

    fake = sub.add_parser("fake-shop", help="lancer le faux magasin de démonstration")
    fake.add_argument("--port", type=int, default=8765)
    return parser


# --- Commandes -----------------------------------------------------------------------------


async def _run(settings: Settings, args: argparse.Namespace) -> int:
    retailers = select_retailers(load_retailers(settings.config_dir), args.only)
    if not retailers:
        print("Aucun site activé dans config/retailers/.", file=sys.stderr)
        return 1
    if args.interval is not None and args.interval < 0.1:
        print("--interval doit valoir au moins 0.1 minute.", file=sys.stderr)
        return 2
    notifier, close_notifier = _make_notifier(settings)
    storage = Storage(settings.db_path)
    try:
        async with PoliteClient(settings.user_agent) as client:
            engine = Engine(retailers, storage, client, notifier, settings.detection())
            log.info("pricebot %s : %s", __version__, ", ".join(r.name for r in retailers))
            if args.once:
                report = await engine.run_cycle()
                print(f"Passage terminé : {report.summary()}")
                return 0
            minutes = args.interval or settings.check_interval_minutes
            log.info("Un passage toutes les %s minutes. Arrêt : Ctrl+C", minutes)
            await engine.run_forever(
                timedelta(minutes=minutes), after_cycle=_heartbeat(settings.healthcheck_url)
            )
    finally:
        storage.close()
        await close_notifier()
    return 0


async def _check(settings: Settings, args: argparse.Namespace) -> int:
    host = urlsplit(args.url).netloc
    interval = 5.0
    if settings.config_dir.is_dir():
        for retailer in load_retailers(settings.config_dir):
            if urlsplit(retailer.base_url).netloc == host:
                interval = retailer.min_interval_seconds
    async with PoliteClient(settings.user_agent) as client:
        try:
            html = await client.get_text(args.url, min_interval=interval)
        except FetchError as error:
            print(f"Impossible de lire la page : {error}")
            return 1
    data = extract_page(html, args.url)
    for offer in data.products:
        print("Produit :")
        _print_offer(offer)
    if data.listing:
        print(f"Page de liste : {len(data.listing)} produits")
        for offer in data.listing[: args.limit]:
            print(
                f"  {format_price(offer.price, offer.currency):>14}  {offer.availability.value:<12}"
                f"  {offer.title[:70]}"
            )
    if not data.products and not data.listing:
        print("Aucun prix trouvé dans les données structurées de cette page.")
        return 1
    return 0


async def _telegram_test(settings: Settings, args: argparse.Namespace) -> int:
    if not settings.telegram_token or not settings.telegram_configured:
        print(
            "PRICEBOT_TELEGRAM_TOKEN est vide : collez le jeton de @BotFather dans le fichier .env."
        )
        return 1
    notifier = TelegramNotifier(
        settings.telegram_token.get_secret_value().strip(), settings.telegram_chat_id or ""
    )
    try:
        print(f"Bot reconnu : {await notifier.bot_name()}")
        if not settings.telegram_chat_id:
            chats = await notifier.find_chats()
            if not chats:
                print(
                    "Aucune conversation trouvée. Ajoutez le bot à votre groupe, envoyez-y /start,"
                    " puis relancez cette commande."
                )
                return 1
            print("Conversations trouvées :")
            for chat_id, name in chats:
                print(f"  {chat_id}   {name}")
            print(
                "Copiez l'identifiant de votre groupe dans PRICEBOT_TELEGRAM_CHAT_ID"
                " (fichier .env), puis relancez cette commande pour recevoir un message de test."
            )
            return 0
        await notifier.send("✅ <b>pricebot</b> est bien configuré : les alertes arriveront ici.")
        print("Message de test envoyé : vérifiez votre groupe Telegram.")
        return 0
    except NotificationError as error:
        print(f"Échec : {error}")
        return 1
    finally:
        await notifier.aclose()


async def _stats(settings: Settings, args: argparse.Namespace) -> int:
    if not settings.db_path.exists():
        print("Pas encore de base : lancez d'abord « pricebot run ».")
        return 1
    storage = Storage(settings.db_path)
    try:
        counts = storage.counts()
    finally:
        storage.close()
    labels = {
        "offers": "Offres suivies",
        "price_observations": "Changements de prix enregistrés",
        "anomalies_alerted": "Erreurs de prix en cours",
        "anomalies_resolved": "Erreurs de prix terminées",
        "anomalies_rejected": "Fausses alertes écartées",
        "anomalies_failed": "Alertes non envoyées",
    }
    for key, value in counts.items():
        label = labels.get(key) or f"Offres sur {key.removeprefix('offers_')}"
        print(f"{label:<36} {value}")
    return 0


_COMMANDS: dict[str, Command] = {
    "run": _run,
    "check": _check,
    "telegram-test": _telegram_test,
    "stats": _stats,
}


# --- Utilitaires ---------------------------------------------------------------------------


def _make_notifier(settings: Settings) -> tuple[Notifier, Callable[[], Awaitable[None]]]:
    if settings.telegram_token and settings.telegram_configured and settings.telegram_chat_id:
        telegram = TelegramNotifier(
            settings.telegram_token.get_secret_value().strip(), settings.telegram_chat_id
        )
        return telegram, telegram.aclose
    if settings.telegram_configured:
        log.warning("PRICEBOT_TELEGRAM_CHAT_ID manquant : alertes affichées dans ce terminal.")
    else:
        log.warning("Telegram non configuré : alertes affichées dans ce terminal.")

    async def nothing() -> None:
        return None

    return ConsoleNotifier(), nothing


def _heartbeat(url: str | None) -> Callable[[CycleReport], Awaitable[None]] | None:
    if not url:
        return None

    async def ping(report: CycleReport) -> None:
        target = url.rstrip("/") + ("/fail" if report.pages == 0 and report.errors else "")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.get(target)
        except httpx.HTTPError as error:
            log.warning("Ping de surveillance impossible : %s", type(error).__name__)

    return ping


def _print_offer(offer: RawOffer) -> None:
    rows = [
        ("Titre", offer.title),
        ("Prix", format_price(offer.price, offer.currency)),
        (
            "Prix barré",
            format_price(offer.list_price, offer.currency) if offer.list_price else None,
        ),
        ("Disponibilité", offer.availability.value),
        ("État", offer.condition.value),
        ("Vendeur", offer.seller),
        ("EAN", offer.gtin),
        ("Marque", offer.brand),
        ("URL", offer.url),
    ]
    for label, value in rows:
        if value:
            print(f"  {label:<14} {value}")


def _configure_logging(verbose: bool, log_dir: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                log_dir / "pricebot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
            )
        )
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )
    # httpx journalise chaque URL appelée, y compris celle de Telegram qui contient le jeton
    # secret : on la fait taire, même en mode détaillé.
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _fix_console_encoding() -> None:
    # Évite un plantage si la console Windows ne sait pas afficher un caractère.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="replace")
