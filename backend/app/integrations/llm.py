from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from collections.abc import Iterator


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

    async def complete(self, prompt: str) -> str:
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

    async def stream_complete(self, prompt: str):
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
            "stream": True,
        }
        queue: asyncio.Queue[str | BaseException | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def worker() -> None:
            try:
                for chunk in _iter_stream_chunks(
                    url=f"{self.base_url}/chat/completions",
                    payload=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout_seconds=self.timeout_seconds,
                ):
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            except BaseException as exc:
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        task = asyncio.create_task(asyncio.to_thread(worker))
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, BaseException):
                    raise item
                yield item
        finally:
            await task


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


_STREAM_DONE = object()


def _iter_stream_chunks(
    *,
    url: str,
    payload: dict,
    headers: dict[str, str],
    timeout_seconds: float,
) -> Iterator[str]:
    encoded = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=encoded,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            **headers,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or line.startswith(":") or not line.startswith("data:"):
                    continue
                parsed = _parse_stream_data(line.removeprefix("data:").strip())
                if parsed is _STREAM_DONE:
                    break
                if parsed:
                    yield parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def _parse_stream_data(data: str) -> str | object | None:
    if data == "[DONE]":
        return _STREAM_DONE

    try:
        event = json.loads(data)
        delta = event["choices"][0].get("delta", {})
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("LLM stream response did not contain completion text") from exc

    content = delta.get("content")
    if content is None:
        return None
    return str(content)
