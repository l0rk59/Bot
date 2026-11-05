from pathlib import Path

import pytest

from pricebot.retailers import ConfigError, RetailerConfig, load_retailers, select_retailers

REPO_CONFIG = Path(__file__).parent.parent / "config" / "retailers"


def write(directory: Path, name: str, content: str) -> None:
    (directory / name).write_text(content, encoding="utf-8")


def test_shipped_configuration_is_valid() -> None:
    retailers = {r.id: r for r in load_retailers(REPO_CONFIG)}
    assert retailers["ldlc"].enabled
    assert retailers["ldlc"].min_interval_seconds >= 5
    assert not retailers["fake-shop"].enabled
    # Seule la page 1 des catégories LDLC contient des prix (voir le commentaire du YAML).
    assert len(retailers["ldlc"].listings) >= 30
    assert all(listing.max_pages == 1 for listing in retailers["ldlc"].listings)
    assert all(url.url.startswith("https://www.ldlc.com/") for url in retailers["ldlc"].listings)


def test_real_sites_must_stay_polite(tmp_path: Path) -> None:
    write(
        tmp_path,
        "trop-rapide.yaml",
        "id: rapide\nname: R\nbase_url: https://r.example\nmin_interval_seconds: 0.2\n",
    )
    with pytest.raises(ConfigError, match="au moins"):
        load_retailers(tmp_path)


def test_unknown_keys_are_refused(tmp_path: Path) -> None:
    write(tmp_path, "faute.yaml", "id: x\nname: X\nbase_url: https://x.example\nlistngs: []\n")
    with pytest.raises(ConfigError, match=r"faute\.yaml"):
        load_retailers(tmp_path)


def test_duplicate_ids_are_refused(tmp_path: Path) -> None:
    for name in ("a.yaml", "b.yaml"):
        write(tmp_path, name, "id: same\nname: S\nbase_url: https://s.example\n")
    with pytest.raises(ConfigError, match="double"):
        load_retailers(tmp_path)


def test_windows_bom_is_accepted(tmp_path: Path) -> None:
    (tmp_path / "bom.yaml").write_text(
        "id: bom\nname: B\nbase_url: https://b.example\n", encoding="utf-8-sig"
    )
    assert load_retailers(tmp_path)[0].id == "bom"


def test_missing_directory() -> None:
    with pytest.raises(ConfigError, match="introuvable"):
        load_retailers(Path("n-existe-pas"))


def test_select_retailers() -> None:
    on = RetailerConfig(id="on", name="On", base_url="https://on.example")
    off = RetailerConfig(id="off", name="Off", base_url="https://off.example", enabled=False)
    assert select_retailers([on, off]) == [on]
    assert select_retailers([on, off], ["off"]) == [off]  # demandé explicitement
    with pytest.raises(ConfigError, match="inconnu"):
        select_retailers([on, off], ["nope"])


def test_pagination_and_sellers() -> None:
    retailer = RetailerConfig(
        id="r", name="Rue", base_url="https://r.example", own_seller_names=["RUE SAS"]
    )
    assert retailer.page_url("https://r.example/c/", 1) == "https://r.example/c/"
    assert retailer.page_url("https://r.example/c/", 2) is None  # pas de pagination
    assert retailer.is_own_seller(None)
    assert retailer.is_own_seller("rue sas")
    assert retailer.is_own_seller("Rue")
    assert not retailer.is_own_seller("Vendeur Tiers")
    with pytest.raises(ValueError, match="page"):
        RetailerConfig(id="r", name="R", base_url="https://r.example", page_url_template="{url}p")
