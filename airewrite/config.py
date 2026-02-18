from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ProviderName = Literal["openai", "anthropic"]


@dataclass(frozen=True)
class Settings:
    """Settings."""

    provider: ProviderName
    model: str
    explain: bool
    mode: str


def config_dir() -> Path:
    """Get config directory."""
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / "airewrite"
    return Path.home() / ".config" / "airewrite"


def get_api_key(provider: ProviderName) -> str | None:
    """Get API key."""
    if provider == "openai":
        return os.environ.get("OPENAI_API_KEY")
    return os.environ.get("ANTHROPIC_API_KEY")
