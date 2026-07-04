import asyncio
import inspect
import unittest
from unittest.mock import patch

from app.integrations.llm import OpenAICompatibleClient


class LlmClientTests(unittest.TestCase):
    def test_complete_does_not_accept_max_tokens(self):
        parameters = inspect.signature(OpenAICompatibleClient.complete).parameters

        self.assertNotIn("max_tokens", parameters)

    def test_complete_omits_max_tokens_from_payload(self):
        captured = {}

        def fake_post_json(*, url, payload, headers, timeout_seconds):
            captured["url"] = url
            captured["payload"] = payload
            captured["headers"] = headers
            captured["timeout_seconds"] = timeout_seconds
            return {"choices": [{"message": {"content": "Generated text"}}]}

        client = OpenAICompatibleClient(
            api_key="test-key",
            base_url="https://model.example.com/v1",
            model="demo-model",
            timeout_seconds=12,
        )

        with patch("app.integrations.llm._post_json", fake_post_json):
            result = asyncio.run(client.complete("Write something"))

        self.assertEqual(result, "Generated text")
        self.assertEqual(captured["payload"]["model"], "demo-model")
        self.assertNotIn("max_tokens", captured["payload"])
        self.assertEqual(captured["url"], "https://model.example.com/v1/chat/completions")
        self.assertEqual(captured["headers"], {"Authorization": "Bearer test-key"})
        self.assertEqual(captured["timeout_seconds"], 12)

    def test_stream_complete_sends_stream_request_without_max_tokens(self):
        captured = {}

        def fake_iter_stream_chunks(*, url, payload, headers, timeout_seconds):
            captured["url"] = url
            captured["payload"] = payload
            captured["headers"] = headers
            captured["timeout_seconds"] = timeout_seconds
            return iter(["Hello", " world"])

        async def collect_chunks():
            client = OpenAICompatibleClient(
                api_key="test-key",
                base_url="https://model.example.com/v1",
                model="demo-model",
                timeout_seconds=12,
            )
            chunks = []
            async for chunk in client.stream_complete("Write something"):
                chunks.append(chunk)
            return chunks

        with patch("app.integrations.llm._iter_stream_chunks", fake_iter_stream_chunks):
            result = asyncio.run(collect_chunks())

        self.assertEqual(result, ["Hello", " world"])
        self.assertEqual(captured["payload"]["model"], "demo-model")
        self.assertTrue(captured["payload"]["stream"])
        self.assertNotIn("max_tokens", captured["payload"])
        self.assertEqual(captured["url"], "https://model.example.com/v1/chat/completions")
        self.assertEqual(captured["headers"], {"Authorization": "Bearer test-key"})
        self.assertEqual(captured["timeout_seconds"], 12)

    def test_stream_parser_extracts_delta_content(self):
        from app.integrations.llm import _parse_stream_data

        content = _parse_stream_data('{"choices":[{"delta":{"content":"Hi"}}]}')

        self.assertEqual(content, "Hi")


if __name__ == "__main__":
    unittest.main()
