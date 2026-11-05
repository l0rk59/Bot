"""Configuration des sites surveillés : un fichier YAML par site dans config/retailers/."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
MIN_INTERVAL_REAL_SITES = 1.0


class ConfigError(Exception):
    """Fichier de configuration invalide."""


class ListingConfig(BaseModel):
    """Une page de liste (catégorie) à parcourir."""

    model_config = ConfigDict(extra="forbid")

    url: str
    max_pages: int = Field(default=1, ge=1, le=50)


class RetailerConfig(BaseModel):
    """Un site surveillé."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str
    base_url: str
    enabled: bool = True
    country: str = "FR"
    currency: str = "EUR"
    min_interval_seconds: float = Field(default=5.0, ge=0)
    own_seller_names: list[str] = Field(default_factory=list)
    page_url_template: str | None = None
    listings: list[ListingConfig] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_politeness(self) -> RetailerConfig:
        host = urlsplit(self.base_url).hostname or ""
        if host not in LOCAL_HOSTS and self.min_interval_seconds < MIN_INTERVAL_REAL_SITES:
            raise ValueError(
                f"min_interval_seconds doit être d'au moins {MIN_INTERVAL_REAL_SITES} s "
                "pour un vrai site"
            )
        if self.page_url_template is not None and "{page}" not in self.page_url_template:
            raise ValueError("page_url_template doit contenir {page}")
        return self

    def page_url(self, listing_url: str, page: int) -> str | None:
        """URL de la page n d'une liste (None si le site n'a pas de pagination configurée)."""
        if page == 1:
            return listing_url
        if self.page_url_template is None:
            return None
        return self.page_url_template.format(url=listing_url, page=page)

    def is_own_seller(self, seller: str | None) -> bool:
        """Vrai si le vendeur est le marchand lui-même (ou inconnu)."""
        if not seller:
            return True
        names = {name.casefold() for name in self.own_seller_names} | {self.name.casefold()}
        return seller.casefold() in names


def load_retailers(directory: Path) -> list[RetailerConfig]:
    """Charge tous les fichiers *.yaml d'un dossier."""
    if not directory.is_dir():
        raise ConfigError(f"Dossier de configuration introuvable : {directory}")
    retailers: list[RetailerConfig] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            content = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
            retailers.append(RetailerConfig.model_validate(content))
        except (yaml.YAMLError, ValidationError) as error:
            raise ConfigError(f"{path.name} : {error}") from error
    ids = [retailer.id for retailer in retailers]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ConfigError(f"Identifiants en double : {', '.join(sorted(duplicates))}")
    return retailers


def select_retailers(
    retailers: list[RetailerConfig], only: list[str] | None = None
) -> list[RetailerConfig]:
    """Sites à surveiller : ceux demandés explicitement, sinon tous ceux activés."""
    if not only:
        return [retailer for retailer in retailers if retailer.enabled]
    known = {retailer.id: retailer for retailer in retailers}
    unknown = [ident for ident in only if ident not in known]
    if unknown:
        raise ConfigError(f"Site(s) inconnu(s) : {', '.join(unknown)}")
    return [known[ident] for ident in only]
