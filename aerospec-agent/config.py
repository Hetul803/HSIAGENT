"""Application configuration helpers."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    app_title: str = "AeroSpec Agent"
    app_subtitle: str = "Trustworthy Hyperspectral Mission Design Copilot for Aviation"
    data_dir: Path = Path(__file__).resolve().parent / "data"


settings = Settings()
