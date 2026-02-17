from __future__ import annotations

import httpx

from airewrite.providers.base import Message, ProviderError


class AnthropicProvider:
    """Anthropic provider."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        anthropic_version: str = "2023-06-01",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._anthropic_version = anthropic_version

    def generate(self, *, messages: list[Message], model: str) -> str:
        """Generate text using the Anthropic API."""
        url = f"{self._base_url}/v1/messages"

        system_parts: list[str] = []
        user_parts: list[str] = []
        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
            else:
                user_parts.append(m.content)

        payload = {
            "model": model,
            "max_tokens": 1024,
            "system": "\n\n".join(system_parts).strip() or None,
            "messages": [{"role": "user", "content": "\n\n".join(user_parts).strip()}],
        }

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": self._anthropic_version,
            "content-type": "application/json",
        }

        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload, headers=headers)

        if resp.status_code >= 400:
            raise ProviderError(f"Anthropic API error: {resp.status_code} {resp.text}")

        data = resp.json()
        try:
            parts = data["content"]
            text = "".join(p.get("text", "") for p in parts)
            return text.strip()
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Anthropic API response parse error: {e}") from e
