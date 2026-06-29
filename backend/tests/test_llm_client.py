import asyncio
import unittest
from unittest.mock import patch

from app.integrations.llm import OpenAICompatibleClient


class LlmClientTests(unittest.TestCase):
    def test_complete_includes_max_tokens_when_supplied(self):
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
            result = asyncio.run(client.complete("Write something", max_tokens=140))

        self.assertEqual(result, "Generated text")
        self.assertEqual(captured["payload"]["model"], "demo-model")
        self.assertEqual(captured["payload"]["max_tokens"], 140)
        self.assertEqual(captured["url"], "https://model.example.com/v1/chat/completions")
        self.assertEqual(captured["headers"], {"Authorization": "Bearer test-key"})
        self.assertEqual(captured["timeout_seconds"], 12)


if __name__ == "__main__":
    unittest.main()
