"""Client HTTP poli : débit limité par site, respect de robots.txt, nouvelles tentatives.

Aucun contournement : si un site refuse l'accès (401, 403) ou l'interdit dans robots.txt,
la requête échoue et le site est laissé tranquille.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx
from protego import Protego

log = logging.getLogger(__name__)

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
BLOCKED_STATUSES = frozenset({401, 403})
ROBOTS_TTL = 24 * 3600.0
ROBOTS_ERROR_RETRY = 5 * 60.0
MAX_RETRY_AFTER = 15 * 60.0


class FetchError(Exception):
    """La page n'a pas pu être récupérée."""

    def __init__(self, url: str, reason: str, status: int | None = None) -> None:
        super().__init__(f"{url} : {reason}")
        self.url = url
        self.status = status


class RobotsDisallowed(FetchError):
    """robots.txt interdit cette page à notre robot."""


class Blocked(FetchError):
    """Le site refuse l'accès au robot (401/403) : on ne force pas."""


@dataclass
class _HostState:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_request: float | None = None
    robots: Protego | None = None
    robots_checked_at: float | None = None
    robots_disallow_all: bool = False
    robots_ttl: float = ROBOTS_TTL


class PoliteClient:
    """Client HTTP partagé par tous les connecteurs."""

    def __init__(
        self,
        user_agent: str,
        *,
        robots_token: str = "pricebot",
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 20.0,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.6",
            },
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )
        self._robots_token = robots_token
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._sleep = sleep
        self._clock = clock
        self._hosts: dict[str, _HostState] = {}

    async def __aenter__(self) -> PoliteClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_text(self, url: str, *, min_interval: float) -> str:
        """Récupère une page en respectant robots.txt et le débit du site."""
        origin = _origin(url)
        state = self._hosts.setdefault(origin, _HostState())
        async with state.lock:
            await self._ensure_robots(origin, state, min_interval)
            if not self._allowed(state, url):
                raise RobotsDisallowed(url, "interdit par robots.txt")
            interval = max(min_interval, self._crawl_delay(state))
            response = await self._fetch(url, state, interval)
            return response.text

    # --- robots.txt ----------------------------------------------------------------------

    async def _ensure_robots(self, origin: str, state: _HostState, interval: float) -> None:
        now = self._clock()
        if state.robots_checked_at is not None and now - state.robots_checked_at < state.robots_ttl:
            return
        robots_url = f"{origin}/robots.txt"
        state.robots, state.robots_disallow_all = None, False
        state.robots_ttl = ROBOTS_TTL
        try:
            response = await self._fetch(robots_url, state, interval, accept_client_errors=True)
        except FetchError as error:
            # RFC 9309 : robots.txt injoignable (5xx, réseau) = tout est interdit pour l'instant.
            log.warning("robots.txt injoignable pour %s (%s) : pause de ce site", origin, error)
            state.robots_disallow_all = True
            state.robots_ttl = ROBOTS_ERROR_RETRY
        else:
            if response.status_code == 200:
                state.robots = Protego.parse(response.text)
            # 4xx : pas de robots.txt, tout est autorisé (RFC 9309).
        state.robots_checked_at = self._clock()

    def _allowed(self, state: _HostState, url: str) -> bool:
        if state.robots_disallow_all:
            return False
        if state.robots is None:
            return True
        return bool(state.robots.can_fetch(url, self._robots_token))

    def _crawl_delay(self, state: _HostState) -> float:
        if state.robots is None:
            return 0.0
        delay = state.robots.crawl_delay(self._robots_token)
        return float(delay) if delay else 0.0

    # --- Requêtes ------------------------------------------------------------------------

    async def _fetch(
        self,
        url: str,
        state: _HostState,
        interval: float,
        *,
        accept_client_errors: bool = False,
    ) -> httpx.Response:
        attempt = 0
        while True:
            await self._wait_turn(state, interval)
            response: httpx.Response | None = None
            status: int | None = None
            try:
                response = await self._client.get(url)
            except httpx.TransportError as error:
                reason = f"erreur réseau ({type(error).__name__})"
            else:
                status = response.status_code
                if status < 400:
                    return response
                if status in BLOCKED_STATUSES and not accept_client_errors:
                    raise Blocked(url, f"accès refusé (HTTP {status})", status)
                if status not in RETRY_STATUSES:
                    if accept_client_errors and status < 500:
                        return response
                    raise FetchError(url, f"HTTP {status}", status)
                reason = f"HTTP {status}"
            if attempt >= self._max_retries:
                raise FetchError(url, f"{reason} après {attempt + 1} tentatives", status)
            delay = self._retry_delay(attempt, response)
            log.info("%s : %s, nouvelle tentative dans %.0f s", url, reason, delay)
            await self._sleep(delay)
            attempt += 1

    async def _wait_turn(self, state: _HostState, interval: float) -> None:
        if state.last_request is not None:
            wait = state.last_request + interval - self._clock()
            if wait > 0:
                await self._sleep(wait)
        state.last_request = self._clock()

    def _retry_delay(self, attempt: int, response: httpx.Response | None) -> float:
        delay: float = self._backoff_base * (2.0**attempt)
        if response is not None:
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            if retry_after is not None:
                delay = max(delay, retry_after)
        return min(delay, MAX_RETRY_AFTER)


def _origin(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise FetchError(url, "URL invalide")
    return f"{parts.scheme}://{parts.netloc}"


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        moment = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, float(moment.timestamp()) - time.time())
