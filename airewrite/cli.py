from __future__ import annotations

import json
import shutil
import sys
from datetime import date, datetime
from typing import Annotated, Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from airewrite.config import ProviderName, config_dir, get_api_key
from airewrite.history import (
    HistoryEvent,
    append_event,
    cleanup_history,
    history_root,
    now_utc_iso,
)
from airewrite.modes import load_mode_instructions, mode_path
from airewrite.providers.anthropic import AnthropicProvider
from airewrite.providers.base import LLMProvider, Message, ProviderError, Result, Usage
from airewrite.providers.openai import OpenAIProvider
from airewrite.session import InteractiveSession
from airewrite.stats import estimate_cost_usd, format_stats

app = typer.Typer(add_completion=False)
_console = Console()


def _build_messages(*, instructions: str, explain: bool, text: str) -> list[Message]:
    """Build messages."""
    explain_suffix = (
        ""
        if not explain
        else "\n\nAfter the rewritten text, add a short explanation of what you changed."
    )
    system = f"{instructions}{explain_suffix}".strip()
    return [
        Message(role="system", content=system),
        Message(role="user", content=text),
    ]


def _get_provider(provider: ProviderName) -> LLMProvider:
    """Get provider."""
    api_key = get_api_key(provider)
    if not api_key:
        env = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        raise typer.BadParameter(f"Missing API key. Set {env}.")

    if provider == "openai":
        return OpenAIProvider(api_key=api_key)
    return AnthropicProvider(api_key=api_key)


def _default_model(provider: ProviderName) -> str:
    """Get default model."""
    return "gpt-4o-mini" if provider == "openai" else "claude-3-5-sonnet-20241022"


def _separator_line(char: str = "-") -> str:
    """Get separator line."""
    width = shutil.get_terminal_size(fallback=(80, 24)).columns
    return char * max(10, width)


def _print_config(
    *,
    mode: str,
    provider: ProviderName,
    model: str,
    explain: bool,
    history: bool,
    history_days: int,
    history_dir: str | None,
) -> None:
    """Print config."""
    typer.echo(f"mode: {mode}")
    typer.echo(f"provider: {provider}")
    typer.echo(f"model: {model}")
    typer.echo(f"explain: {explain}")
    typer.echo(f"history: {history}")
    typer.echo(f"history_days: {history_days}")
    typer.echo(f"history_dir: {str(history_root(history_dir))}")
    typer.echo("")


def _print_paths(*, history_dir: str | None) -> None:
    """Print paths."""
    typer.echo(f"config_dir: {str(config_dir())}")
    typer.echo(f"modes_dir: {str(mode_path('rewrite').parent)}")
    typer.echo(f"history_dir: {str(history_root(history_dir))}")


@app.command(name="show-config")
def show_config(
    mode: Annotated[str, typer.Option("--mode", "-m")] = "rewrite",
    provider: Annotated[ProviderName, typer.Option("--provider", "-p")] = "openai",
    model: Annotated[Optional[str], typer.Option("--model")] = None,
    explain: Annotated[bool, typer.Option("--explain")] = False,
    history: Annotated[bool, typer.Option("--history/--no-history")] = True,
    history_days: Annotated[int, typer.Option("--history-days")] = 30,
    history_dir: Annotated[Optional[str], typer.Option("--history-dir")] = None,
):
    """Print the effective configuration (including resolved history location)."""

    model_name = model or _default_model(provider)
    _print_config(
        mode=mode,
        provider=provider,
        model=model_name,
        explain=explain,
        history=history,
        history_days=history_days,
        history_dir=history_dir,
    )


@app.command(name="paths")
def paths(
    history_dir: Annotated[Optional[str], typer.Option("--history-dir")] = None,
):
    """Print resolved paths used by airewrite."""

    _print_paths(history_dir=history_dir)


def _month_start(d: date) -> date:
    """Get the first day of the month."""
    return date(d.year, d.month, 1)


def _parse_month(value: str | None) -> date:
    """Parse a month string."""
    if not value:
        return _month_start(date.today())
    try:
        dt = datetime.strptime(value, "%Y-%m").date()
    except ValueError as e:
        raise typer.BadParameter("--month must be in YYYY-MM format") from e
    return _month_start(dt)


def _compute_spend(
    *, start: date, history_dir: str | None
) -> tuple[dict[str, float], dict[str, int], dict[str, dict[str, int]]]:
    # sourcery skip: extract-duplicate-method
    """Compute spend."""
    root = history_root(history_dir)
    totals: dict[str, float] = {}
    unknown: dict[str, int] = {}
    unknown_reasons: dict[str, dict[str, int]] = {}

    if not root.exists():
        return totals, unknown, unknown_reasons

    for p in sorted(root.glob("*.jsonl")):
        try:
            day = date.fromisoformat(p.stem)
        except ValueError:
            continue
        if day < start:
            continue

        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue

            provider = str(evt.get("provider") or "unknown")
            model = str(evt.get("model") or "")

            cost = evt.get("est_cost_usd")
            if isinstance(cost, (int, float)):
                totals[provider] = totals.get(provider, 0.0) + float(cost)
                continue

            in_tok = evt.get("input_tokens")
            out_tok = evt.get("output_tokens")
            if isinstance(in_tok, int) and isinstance(out_tok, int):
                usage = Usage(input_tokens=in_tok, output_tokens=out_tok)
                est = estimate_cost_usd(provider=provider, model=model, usage=usage)
                if est is not None:
                    totals[provider] = totals.get(provider, 0.0) + est
                else:
                    unknown[provider] = unknown.get(provider, 0) + 1
                    unknown_reasons.setdefault(provider, {}).setdefault(
                        "unknown_model_pricing", 0
                    )
                    unknown_reasons[provider]["unknown_model_pricing"] += 1
            else:
                unknown[provider] = unknown.get(provider, 0) + 1
                unknown_reasons.setdefault(provider, {}).setdefault("missing_tokens", 0)
                unknown_reasons[provider]["missing_tokens"] += 1

    return totals, unknown, unknown_reasons


def _print_spend(*, start: date, history_dir: str | None, verbose: bool) -> None:
    """Print spend."""
    totals, unknown, unknown_reasons = _compute_spend(
        start=start, history_dir=history_dir
    )
    month_label = start.strftime("%Y-%m")

    if not totals and not unknown:
        typer.echo(f"No spend data found for {month_label}.")
        return

    typer.echo(f"Estimated airewrite spend for {month_label} (local history):")
    grand_total = 0.0
    for prov in sorted(totals):
        amt = totals[prov]
        grand_total += amt
        suffix = ""
        if unknown.get(prov):
            suffix = f" (plus {unknown[prov]} unknown)"
        typer.echo(f"- {prov}: ${amt:.4f}{suffix}")

    for prov in sorted(k for k in unknown if k not in totals):
        typer.echo(f"- {prov}: n/a (only unknown: {unknown[prov]})")

    if verbose and unknown_reasons:
        typer.echo("\nUnknown breakdown:")
        for prov in sorted(unknown_reasons):
            reasons = unknown_reasons[prov]
            typer.echo(f"- {prov}:")
            for reason, count in sorted(reasons.items()):
                typer.echo(f"  - {reason}: {count}")

    typer.echo(f"Total: ${grand_total:.4f}")


@app.command(name="spend")
def spend(
    month: Annotated[Optional[str], typer.Option("--month")] = None,
    history_dir: Annotated[Optional[str], typer.Option("--history-dir")] = None,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
):
    """Estimate spend by summing per-request costs from local history."""

    start = _parse_month(month)
    _print_spend(start=start, history_dir=history_dir, verbose=verbose)


@app.command()
def run(
    mode: Annotated[str, typer.Option("--mode", "-m")] = "rewrite",
    provider: Annotated[ProviderName, typer.Option("--provider", "-p")] = "openai",
    model: Annotated[Optional[str], typer.Option("--model")] = None,
    explain: Annotated[bool, typer.Option("--explain")] = False,
    history: Annotated[bool, typer.Option("--history/--no-history")] = True,
    history_days: Annotated[int, typer.Option("--history-days")] = 30,
    history_dir: Annotated[Optional[str], typer.Option("--history-dir")] = None,
    print_config: Annotated[bool, typer.Option("--print-config")] = False,
    pretty: Annotated[bool, typer.Option("--pretty/--no-pretty")] = True,
    stats: Annotated[bool, typer.Option("--stats/--no-stats")] = False,
):
    """Rewrite text using an LLM. If stdin is piped, processes once; otherwise starts an interactive session."""

    instructions = load_mode_instructions(mode)
    provider_client = _get_provider(provider)
    model_name = model or _default_model(provider)

    if print_config:
        _print_config(
            mode=mode,
            provider=provider,
            model=model_name,
            explain=explain,
            history=history,
            history_days=history_days,
            history_dir=history_dir,
        )

    if history:
        cleanup_history(keep_days=history_days, history_dir=history_dir)

    if not sys.stdin.isatty():
        text = sys.stdin.read()
        messages = _build_messages(
            instructions=instructions, explain=explain, text=text
        )
        try:
            result: Result = provider_client.generate(
                messages=messages, model=model_name
            )
        except ProviderError as e:
            raise typer.Exit(code=1) from e

        out = result.text
        usage = result.usage
        est_cost = (
            estimate_cost_usd(provider=provider, model=model_name, usage=usage)
            if usage is not None
            else None
        )

        if history:
            append_event(
                HistoryEvent(
                    timestamp=now_utc_iso(),
                    mode=mode,
                    provider=provider,
                    model=model_name,
                    explain=explain,
                    input_text=text,
                    output_text=out,
                    input_tokens=usage.input_tokens if usage is not None else None,
                    output_tokens=usage.output_tokens if usage is not None else None,
                    est_cost_usd=est_cost,
                ),
                history_dir=history_dir,
            )

        if stats and result.usage is not None:
            typer.echo(
                format_stats(provider=provider, model=model_name, usage=result.usage),
                err=True,
            )

        sys.stdout.write(out)
        if not out.endswith("\n"):
            sys.stdout.write("\n")
        return

    session = InteractiveSession()

    cur_mode = mode
    cur_provider: ProviderName = provider
    cur_model = model_name
    cur_explain = explain
    cur_pretty = pretty
    cur_stats = stats

    while True:
        block = session.read_block(
            mode=cur_mode, provider=cur_provider, model=cur_model
        )
        if block is None:
            break

        stripped = block.strip()
        if not stripped:
            continue

        if stripped.startswith(":"):
            parts = stripped[1:].split()
            cmd = parts[0] if parts else ""
            arg = parts[1] if len(parts) > 1 else None

            if cmd in {"quit", "q", "exit"}:
                break
            if cmd in {"show", "config"}:
                _print_config(
                    mode=cur_mode,
                    provider=cur_provider,
                    model=cur_model,
                    explain=cur_explain,
                    history=history,
                    history_days=history_days,
                    history_dir=history_dir,
                )
                continue
            if cmd == "where":
                _print_paths(history_dir=history_dir)
                continue
            if cmd == "mode" and arg:
                cur_mode = arg
                instructions = load_mode_instructions(cur_mode)
                continue
            if cmd == "provider" and arg in {"openai", "anthropic"}:
                cur_provider = arg  # type: ignore[assignment]
                provider_client = _get_provider(cur_provider)
                if model is None:
                    cur_model = _default_model(cur_provider)
                continue
            if cmd == "model" and arg:
                cur_model = arg
                continue
            if cmd == "explain":
                cur_explain = not cur_explain
                continue
            if cmd == "pretty":
                cur_pretty = not cur_pretty
                typer.echo(f"pretty: {cur_pretty}")
                continue
            if cmd == "stats":
                cur_stats = not cur_stats
                typer.echo(f"stats: {cur_stats}")
                continue
            if cmd == "spend":
                month_arg = None
                verbose_arg = False
                extra = parts[1:]
                for token in extra:
                    if token == "verbose":
                        verbose_arg = True
                    else:
                        month_arg = token

                try:
                    start = _parse_month(month_arg)
                except typer.BadParameter as e:
                    typer.echo(str(e), err=True)
                    continue

                _print_spend(start=start, history_dir=history_dir, verbose=verbose_arg)
                continue

            typer.echo("Unknown command.", err=True)
            continue

        messages = _build_messages(
            instructions=instructions,
            explain=cur_explain,
            text=block,
        )

        try:
            result = provider_client.generate(messages=messages, model=cur_model)
        except ProviderError as e:
            typer.echo(str(e), err=True)
            continue

        out = result.text
        usage = result.usage
        est_cost = (
            estimate_cost_usd(provider=cur_provider, model=cur_model, usage=usage)
            if usage is not None
            else None
        )

        if history:
            append_event(
                HistoryEvent(
                    timestamp=now_utc_iso(),
                    mode=cur_mode,
                    provider=cur_provider,
                    model=cur_model,
                    explain=cur_explain,
                    input_text=block,
                    output_text=out,
                    input_tokens=usage.input_tokens if usage is not None else None,
                    output_tokens=usage.output_tokens if usage is not None else None,
                    est_cost_usd=est_cost,
                ),
                history_dir=history_dir,
            )

        if cur_pretty:
            title = f"{cur_mode} | {cur_provider} | {cur_model}"
            _console.print(Rule(title, style="cyan"))
            _console.print(Panel(out, border_style="cyan", box=box.HORIZONTALS))
        else:
            sep = _separator_line("-")
            sys.stdout.write(f"{sep}\n")
            sys.stdout.write(out)
            if not out.endswith("\n"):
                sys.stdout.write("\n")
            sys.stdout.write(f"{sep}\n")

        if cur_stats and result.usage is not None:
            _console.print(
                format_stats(
                    provider=cur_provider, model=cur_model, usage=result.usage
                ),
                style="dim",
            )


@app.command()
def version():
    """Prints the version of the tool."""
    try:
        try:
            from importlib.metadata import PackageNotFoundError, version
        except ImportError:
            from importlib_metadata import PackageNotFoundError, version

        try:
            airewrite_version = version("airewrite")
            _console.print(f"airewrite version {airewrite_version}")
        except PackageNotFoundError:
            _console.print(
                "[red]Package not found. Did you install with pip or uv?[/red]"
            )
    except ImportError:
        _console.print("[red]importlib.metadata and importlib_metadata not found[/red]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Main callback."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)
