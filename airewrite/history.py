from __future__ import annotations

import contextlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from airewrite.config import config_dir


@dataclass(frozen=True)
class HistoryEvent:
    """History event."""

    timestamp: str
    mode: str
    provider: str
    model: str
    explain: bool
    input_text: str
    output_text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    est_cost_usd: float | None = None


def history_root(history_dir: str | None = None) -> Path:
    """Get history root."""
    override = history_dir or os.environ.get("AIREWRITE_HISTORY_DIR")
    return Path(override).expanduser() if override else config_dir() / "history"


def history_file_for_day(day: date, *, history_dir: str | None = None) -> Path:
    """Get history file for day."""
    return history_root(history_dir) / f"{day.isoformat()}.jsonl"


def append_event(event: HistoryEvent, *, history_dir: str | None = None) -> None:
    """Append event to history."""
    root = history_root(history_dir)
    root.mkdir(parents=True, exist_ok=True)

    day = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00")).date()
    path = history_file_for_day(day, history_dir=history_dir)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event), ensure_ascii=False))
        f.write("\n")


def cleanup_history(*, keep_days: int, history_dir: str | None = None) -> None:
    """Cleanup history."""
    if keep_days <= 0:
        return

    root = history_root(history_dir)
    if not root.exists():
        return

    cutoff = date.today() - timedelta(days=keep_days)
    for p in root.glob("*.jsonl"):
        try:
            day = date.fromisoformat(p.stem)
        except ValueError:
            continue
        if day < cutoff:
            with contextlib.suppress(OSError):
                p.unlink()


def now_utc_iso() -> str:
    """Get current time in UTC ISO format."""
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
