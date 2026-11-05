from collections.abc import Callable

import httpx
import pytest
from conftest import FakeMonotonic

from pricebot.http import Blocked, FetchError, PoliteClient, RobotsDisallowed

Handler = Callable[[httpx.Request], httpx.Response]


def make_client(handler: Handler, monotonic: FakeMonotonic) -> PoliteClient:
    return PoliteClient(
        "pricebot-test",
        transport=httpx.MockTransport(handler),
        sleep=monotonic.sleep,
        clock=monotonic,
        backoff_base=1.0,
    )


def site(
    robots: str | None = "User-agent: *\nDisallow: /prive/\n", robots_status: int = 200
) -> tuple[Handler, list[str]]:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/robots.txt":
            if robots is None:
                return httpx.Response(robots_status)
            return httpx.Response(robots_status, text=robots)
        return httpx.Response(200, text=f"page {request.url.path}")

    return handler, calls


async def test_respects_robots_txt(monotonic: FakeMonotonic) -> None:
    handler, calls = site()
    async with make_client(handler, monotonic) as client:
        assert await client.get_text("https://shop.example/ok", min_interval=0) == "page /ok"
        with pytest.raises(RobotsDisallowed):
            await client.get_text("https://shop.example/prive/x", min_interval=0)
    assert calls == ["/robots.txt", "/ok"]  # robots.txt lu une seule fois, page interdite non lue


async def test_robots_wildcards_are_supported(monotonic: FakeMonotonic) -> None:
    handler, _ = site("User-agent: *\nDisallow: /*/produits/page*\n")
    async with make_client(handler, monotonic) as client:
        await client.get_text("https://shop.example/r/1/tv/", min_interval=0)
        with pytest.raises(RobotsDisallowed):
            await client.get_text("https://shop.example/r/1/produits/page2", min_interval=0)


async def test_robots_rules_for_our_bot_name(monotonic: FakeMonotonic) -> None:
    handler, _ = site("User-agent: pricebot\nDisallow: /\n\nUser-agent: *\nAllow: /\n")
    async with make_client(handler, monotonic) as client:
        with pytest.raises(RobotsDisallowed):
            await client.get_text("https://shop.example/", min_interval=0)


async def test_missing_robots_txt_allows_everything(monotonic: FakeMonotonic) -> None:
    handler, _ = site(robots=None, robots_status=404)
    async with make_client(handler, monotonic) as client:
        assert await client.get_text("https://shop.example/x", min_interval=0) == "page /x"


async def test_unreachable_robots_txt_pauses_the_site(monotonic: FakeMonotonic) -> None:
    handler, calls = site(robots=None, robots_status=503)
    async with make_client(handler, monotonic) as client:
        with pytest.raises(RobotsDisallowed):
            await client.get_text("https://shop.example/x", min_interval=0)
    assert "/x" not in calls


async def test_waits_between_requests_to_the_same_site(monotonic: FakeMonotonic) -> None:
    handler, _ = site()
    async with make_client(handler, monotonic) as client:
        await client.get_text("https://shop.example/a", min_interval=5)
        await client.get_text("https://shop.example/b", min_interval=5)
        await client.get_text("https://autre.example/c", min_interval=5)
    # robots.txt → /a, /a → /b, puis robots.txt de l'autre site → /c. Le robots.txt de l'autre
    # site n'attend pas : chaque site a son propre rythme (sinon il y aurait 4 attentes).
    assert monotonic.sleeps == [5, 5, 5]


async def test_crawl_delay_is_honoured(monotonic: FakeMonotonic) -> None:
    handler, _ = site("User-agent: *\nCrawl-delay: 10\n")
    async with make_client(handler, monotonic) as client:
        await client.get_text("https://shop.example/a", min_interval=2)
        await client.get_text("https://shop.example/b", min_interval=2)
    assert monotonic.sleeps == [10, 10]


async def test_retries_temporary_errors_with_retry_after(monotonic: FakeMonotonic) -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(503, headers={"Retry-After": "30"})
        return httpx.Response(200, text="enfin")

    async with make_client(handler, monotonic) as client:
        assert await client.get_text("https://shop.example/x", min_interval=0) == "enfin"
    assert monotonic.sleeps.count(30) == 2


async def test_gives_up_after_max_retries(monotonic: FakeMonotonic) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(500)

    async with make_client(handler, monotonic) as client:
        with pytest.raises(FetchError, match="4 tentatives"):
            await client.get_text("https://shop.example/x", min_interval=0)


async def test_network_errors_are_retried(monotonic: FakeMonotonic) -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise httpx.ConnectError("coupure", request=request)
        return httpx.Response(200, text="ok")

    async with make_client(handler, monotonic) as client:
        assert await client.get_text("https://shop.example/x", min_interval=0) == "ok"


async def test_access_denied_is_not_forced(monotonic: FakeMonotonic) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(403, text="Accès refusé")

    async with make_client(handler, monotonic) as client:
        with pytest.raises(Blocked):
            await client.get_text("https://shop.example/x", min_interval=0)
    assert calls == ["/robots.txt", "/x"]  # aucune nouvelle tentative


async def test_not_found_is_not_retried(monotonic: FakeMonotonic) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with make_client(handler, monotonic) as client:
        with pytest.raises(FetchError) as error:
            await client.get_text("https://shop.example/x", min_interval=0)
    assert error.value.status == 404


async def test_invalid_url(monotonic: FakeMonotonic) -> None:
    handler, _ = site()
    async with make_client(handler, monotonic) as client:
        with pytest.raises(FetchError, match="URL invalide"):
            await client.get_text("ftp://shop.example/x", min_interval=0)
