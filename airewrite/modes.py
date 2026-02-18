from __future__ import annotations

from pathlib import Path

from airewrite.config import config_dir

_DEFAULT_MODES: dict[str, str] = {
    "proofread": "You are a careful proofreader. Fix grammar, spelling, punctuation, and obvious clarity issues. Preserve meaning and tone. Return only the improved text.",
    "rewrite": "Rewrite the text for clarity and flow while preserving meaning and tone. Return only the rewritten text.",
    "professional": "Rewrite the text to sound professional, clear, and confident. Return only the rewritten text.",
    "concise": "Rewrite the text to be significantly more concise while preserving meaning. Remove redundancy and filler. Return only the rewritten text.",
}


def mode_path(mode: str) -> Path:
    """Get the path to the mode file."""
    return config_dir() / "modes" / f"{mode}.md"


def load_mode_instructions(mode: str) -> str:
    """Load the mode instructions."""
    p = mode_path(mode)
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    if mode in _DEFAULT_MODES:
        return _DEFAULT_MODES[mode]
    return _DEFAULT_MODES["rewrite"]
