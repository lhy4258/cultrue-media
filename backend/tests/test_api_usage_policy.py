import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.api import routes
from app.core.config import AppConfig


class ApiUsagePolicyTests(unittest.TestCase):
    def setUp(self):
        routes._usage_guard = None
        routes._usage_guard_signature = None

    def test_model_endpoint_policy_returns_429_after_rate_limit(self):
        config = AppConfig(
            llm_api_key="test-key",
            llm_base_url="https://model.example.com/v1",
            llm_model="demo-model",
            llm_timeout_seconds=30,
            wecom_webhook_url="",
            database_url="postgresql://postgres:postgres@127.0.0.1:5432/culture_media",
            api_rate_limit_per_minute=1,
            llm_daily_request_warning_limit=100,
            api_usage_log_path="",
            frontend_origins=["http://localhost:5173"],
        )
        request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

        routes._begin_model_request(
            config=config,
            request=request,
            endpoint="/api/generate-review",
            platform="google",
            feelings_count=1,
        )

        with self.assertRaises(HTTPException) as context:
            routes._begin_model_request(
                config=config,
                request=request,
                endpoint="/api/generate-review",
                platform="google",
                feelings_count=1,
            )

        self.assertEqual(context.exception.status_code, 429)
        self.assertEqual(context.exception.detail, "请求太频繁，请稍后再试。")


if __name__ == "__main__":
    unittest.main()
