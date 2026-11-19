from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__author__ = "@anhafxd"


class WolfSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SEOWOLF_", env_file=".env", extra="ignore")

    data_dir: Path = Field(default_factory=lambda: Path.home() / ".seowolf")
    database_url: str | None = None

    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        self.data_dir.mkdir(parents=True, exist_ok=True)
        database_file = (self.data_dir / "seowolf.db").resolve()
        return f"sqlite+aiosqlite:///{database_file.as_posix()}"


def load_settings() -> WolfSettings:
    return WolfSettings()
