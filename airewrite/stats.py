from __future__ import annotations

from dataclasses import dataclass

from airewrite.providers.base import Usage


@dataclass(frozen=True)
class ModelRates:
    """Model rates."""

    usd_per_million_input_tokens: float
    usd_per_million_output_tokens: float


_DEFAULT_RATES: dict[tuple[str, str], ModelRates] = {
    ("openai", "gpt-4o-mini"): ModelRates(
        usd_per_million_input_tokens=0.15,
        usd_per_million_output_tokens=0.60,
    ),
    ("anthropic", "claude-3-5-sonnet-20241022"): ModelRates(
        usd_per_million_input_tokens=3.00,
        usd_per_million_output_tokens=15.00,
    ),
}


def estimate_cost_usd(*, provider: str, model: str, usage: Usage) -> float | None:
    """Estimate cost."""
    rates = _DEFAULT_RATES.get((provider, model))
    if rates is None:
        return None

    cost_in = usage.input_tokens * (rates.usd_per_million_input_tokens / 1_000_000)
    cost_out = usage.output_tokens * (rates.usd_per_million_output_tokens / 1_000_000)
    return cost_in + cost_out


def format_stats(*, provider: str, model: str, usage: Usage) -> str:
    """Format stats."""
    cost = estimate_cost_usd(provider=provider, model=model, usage=usage)
    cost_str = "n/a" if cost is None else f"${cost:.6f}"
    return (
        f"tokens: in={usage.input_tokens} out={usage.output_tokens} total={usage.total_tokens}"
        f" | est cost: {cost_str}"
    )
