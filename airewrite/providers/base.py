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


@dataclass(frozen=True)
class Usage:
    """Token usage for a request."""

    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        """Total tokens."""
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class Result:
    """Provider result."""

    text: str
    usage: Usage | None = None


class LLMProvider(Protocol):
    """LLM provider protocol."""

    def generate(self, *, messages: Sequence[Message], model: str) -> Result: ...

    """Generate text using the provider."""
