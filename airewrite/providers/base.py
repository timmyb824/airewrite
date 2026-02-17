from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class Message:
    """A message."""

    role: str
    content: str


class ProviderError(RuntimeError):
    """A provider error."""

    pass


class LLMProvider(Protocol):
    """LLM provider protocol."""

    def generate(self, *, messages: Sequence[Message], model: str) -> str: ...
