"""Réglages lus dans le fichier .env (préfixe PRICEBOT_)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from pricebot import __version__
from pricebot.detection import DetectionSettings


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PRICEBOT_",
        env_file=".env",
        # utf-8-sig : le Bloc-notes de Windows peut ajouter un BOM en début de fichier.
        env_file_encoding="utf-8-sig",
        env_ignore_empty=True,
        extra="ignore",
    )

    telegram_token: SecretStr | None = None
    telegram_chat_id: str | None = None
    db_path: Path = Path("data/pricebot.sqlite3")
    config_dir: Path = Path("config/retailers")
    check_interval_minutes: float = Field(default=15, ge=1)
    max_ratio: Decimal = Field(default=Decimal("0.5"), gt=0, lt=1)
    min_saving: Decimal = Field(default=Decimal("30"), ge=0)
    contact_url: str = "https://github.com/l0rk59/Bot"
    healthcheck_url: str | None = None

    @property
    def user_agent(self) -> str:
        return f"pricebot/{__version__} (+{self.contact_url}; bot personnel de suivi de prix)"

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_token and self.telegram_token.get_secret_value().strip())

    def detection(self) -> DetectionSettings:
        return DetectionSettings(max_ratio=self.max_ratio, min_saving=self.min_saving)
