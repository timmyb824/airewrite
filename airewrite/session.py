from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style


class InteractiveSession:
    """Interactive session."""

    def __init__(self) -> None:
        """Initialize the session."""
        style = Style.from_dict(
            {
                "prompt.title": "ansicyan bold",
                "prompt.pipe": "ansicyan",
                "prompt.hint": "ansibrightblack",
                "prompt.cmd": "ansimagenta",
            }
        )
        self._session = PromptSession(style=style)

    def read_block(self, *, mode: str, provider: str, model: str) -> str | None:
        """Read a block of text."""
        header = FormattedText(
            [
                ("class:prompt.title", "["),
                ("class:prompt.title", mode),
                ("class:prompt.pipe", " | "),
                ("class:prompt.title", provider),
                ("class:prompt.pipe", " | "),
                ("class:prompt.title", model),
                ("class:prompt.title", "]"),
                (
                    "class:prompt.hint",
                    " Paste text. Submit with an empty line. Commands: ",
                ),
                ("class:prompt.cmd", ":help"),
                ("class:prompt.hint", ", "),
                ("class:prompt.cmd", ":mode"),
                ("class:prompt.hint", ", "),
                ("class:prompt.cmd", ":provider"),
                ("class:prompt.hint", ", "),
                ("class:prompt.cmd", ":model"),
                ("class:prompt.hint", ", "),
                ("class:prompt.cmd", ":explain"),
                ("class:prompt.hint", ", "),
                ("class:prompt.cmd", ":pretty"),
                ("class:prompt.hint", ", "),
                ("class:prompt.cmd", ":show"),
                ("class:prompt.hint", ", "),
                ("class:prompt.cmd", ":where"),
                ("class:prompt.hint", ", "),
                ("class:prompt.cmd", ":quit"),
                ("class:prompt.hint", "\n"),
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
