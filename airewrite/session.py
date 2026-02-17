from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText


class InteractiveSession:
    """Interactive session."""

    def __init__(self) -> None:
        """Initialize the session."""
        self._session = PromptSession()

    def read_block(self, *, mode: str, provider: str, model: str) -> str | None:
        """Read a block of text."""
        header = FormattedText(
            [
                ("class:prompt", f"[{mode} | {provider} | {model}]"),
                (
                    "",
                    " Paste text. Submit with an empty line. Commands: :mode, :provider, :model, :quit\n",
                ),
            ]
        )

        lines: list[str] = []
        try:
            first = self._session.prompt(header)
            if first is None:
                return None
            lines.append(first)

            while True:
                line = self._session.prompt("")
                if line == "":
                    break
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            return None

        return "\n".join(lines)
