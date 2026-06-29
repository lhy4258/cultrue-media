from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request


class WeComWebhookClient:
    def __init__(self, *, webhook_url: str, timeout_seconds: float = 10) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds

    async def send_markdown(self, message: str) -> bool:
        if not self.webhook_url:
            return False

        payload = {"msgtype": "markdown", "markdown": {"content": message}}
        try:
            result = await asyncio.to_thread(
                _post_json,
                url=self.webhook_url,
                payload=payload,
                timeout_seconds=self.timeout_seconds,
            )
        except RuntimeError:
            return False

        return result.get("errcode") == 0


def _post_json(*, url: str, payload: dict, timeout_seconds: float) -> dict:
    encoded = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=encoded,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
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

