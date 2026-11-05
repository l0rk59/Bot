from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeClock:
    """Horloge manipulable : les tests avancent le temps à la main."""

    def __init__(self, start: datetime | None = None) -> None:
        self.now = start or datetime(2026, 11, 1, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


class FakeMonotonic:
    """Horloge monotone + sommeil instantané pour tester les délais sans attendre."""

    def __init__(self) -> None:
        self.value = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.value

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def monotonic() -> FakeMonotonic:
    return FakeMonotonic()
