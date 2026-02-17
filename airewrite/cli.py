from __future__ import annotations

import shutil
import sys
from typing import Annotated, Optional

import typer
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
from airewrite.providers.base import Message, ProviderError, LLMProvider
from airewrite.providers.anthropic import AnthropicProvider
from airewrite.providers.openai import OpenAIProvider
from airewrite.session import InteractiveSession

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
            out = provider_client.generate(messages=messages, model=model_name)
        except ProviderError as e:
            raise typer.Exit(code=1) from e

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
                ),
                history_dir=history_dir,
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

            typer.echo("Unknown command.", err=True)
            continue

        messages = _build_messages(
            instructions=instructions,
            explain=cur_explain,
            text=block,
        )

        try:
            out = provider_client.generate(messages=messages, model=cur_model)
        except ProviderError as e:
            typer.echo(str(e), err=True)
            continue

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
                ),
                history_dir=history_dir,
            )

        if cur_pretty:
            title = f"{cur_mode} | {cur_provider} | {cur_model}"
            _console.print(Rule(title, style="cyan"))
            _console.print(Panel(out, border_style="cyan"))
        else:
            sep = _separator_line("-")
            sys.stdout.write(f"{sep}\n")
            sys.stdout.write(out)
            if not out.endswith("\n"):
                sys.stdout.write("\n")
            sys.stdout.write(f"{sep}\n")


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
