from __future__ import annotations

import httpx

from airewrite.providers.base import Message, ProviderError


class OpenAIProvider:
    """OpenAI provider."""

    def __init__(
        self, *, api_key: str, base_url: str = "https://api.openai.com"
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def generate(self, *, messages: list[Message], model: str) -> str:
        """Generate text."""
        url = f"{self._base_url}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload, headers=headers)

        if resp.status_code >= 400:
            raise ProviderError(f"OpenAI API error: {resp.status_code} {resp.text}")

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"OpenAI API response parse error: {e}") from e
