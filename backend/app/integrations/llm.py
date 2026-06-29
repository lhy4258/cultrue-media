from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 30,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def complete(self, prompt: str, max_tokens: int | None = None) -> str:
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY is not configured")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You write concise, realistic customer-facing copy.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        result = await asyncio.to_thread(
            _post_json,
            url=f"{self.base_url}/chat/completions",
            payload=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout_seconds=self.timeout_seconds,
        )

        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("LLM response did not contain completion text") from exc

        return str(content)


def _post_json(
    *,
    url: str,
    payload: dict,
    headers: dict[str, str],
    timeout_seconds: float,
) -> dict:
    encoded = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=encoded,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            **headers,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("HTTP response was not valid JSON") from exc
