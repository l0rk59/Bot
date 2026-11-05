"""La vraie commande `pricebot`, face au faux magasin lancé sur un vrai port local."""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from pricebot.cli import main
from pricebot.fake_shop import FakeShop, make_server


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    """`main` configure la journalisation : on remet tout en place après chaque test."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    for handler in root.handlers:
        if handler not in handlers:
            handler.close()
    root.handlers[:] = handlers
    root.setLevel(level)


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Dossier de travail vide : aucun vrai .env (ni jeton Telegram) n'est lu."""
    monkeypatch.chdir(tmp_path)
    for name in (
        "PRICEBOT_TELEGRAM_TOKEN",
        "PRICEBOT_TELEGRAM_CHAT_ID",
        "PRICEBOT_HEALTHCHECK_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PRICEBOT_DB_PATH", str(tmp_path / "data" / "test.sqlite3"))
    monkeypatch.setenv("PRICEBOT_CONFIG_DIR", str(tmp_path / "retailers"))
    return tmp_path


@pytest.fixture
def live_shop(isolated: Path) -> Iterator[FakeShop]:
    shop = FakeShop()
    server = make_server(shop, "127.0.0.1", 0)  # port libre choisi par le système
    port = server.server_address[1]
    shop.base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = isolated / "retailers"
    config.mkdir()
    (config / "test.yaml").write_text(
        "id: test\nname: Magasin test\n"
        f"base_url: http://127.0.0.1:{port}\n"
        "min_interval_seconds: 0\n"
        'own_seller_names: ["Faux magasin"]\n'
        'page_url_template: "{url}page{page}/"\n'
        "listings:\n"
        f"  - url: http://127.0.0.1:{port}/categorie/\n"
        "    max_pages: 2\n",
        encoding="utf-8",
    )
    yield shop
    server.shutdown()
    server.server_close()


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert "pricebot 0.1.0" in capsys.readouterr().out


def test_stats_without_database(isolated: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["stats"]) == 1
    assert "Pas encore de base" in capsys.readouterr().out


def test_missing_config_directory(isolated: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--once"]) == 2
    assert "introuvable" in capsys.readouterr().err


def test_telegram_test_without_token(isolated: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["telegram-test"]) == 1
    assert "PRICEBOT_TELEGRAM_TOKEN est vide" in capsys.readouterr().out


def test_check_and_full_run_against_the_local_fake_shop(
    live_shop: FakeShop, isolated: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["check", f"{live_shop.base_url}/categorie/"]) == 0
    out = capsys.readouterr().out
    assert "Page de liste : 4 produits" in out

    assert main(["check", live_shop.product_url(1)]) == 0
    assert "EAN            2000000000015" in capsys.readouterr().out

    assert main(["run", "--once"]) == 0
    assert "4 offres lues" in capsys.readouterr().out

    live_shop.set_price(2, "114.99")  # 1 149,90 € → 114,99 € : virgule décalée
    assert main(["run", "--once"]) == 0
    out = capsys.readouterr().out
    assert "Erreur de prix probable" in out  # alerte affichée dans le terminal (sans Telegram)
    assert "1 alertes" in out

    assert main(["stats"]) == 0
    stats = capsys.readouterr().out
    assert "Erreurs de prix en cours" in stats
    assert (isolated / "data" / "pricebot.log").exists()
