import os
import unittest
from pathlib import Path
from unittest.mock import patch

import app.core.config as config_module
from app.core.config import load_config


class ConfigTests(unittest.TestCase):
    def test_default_database_url_uses_project_database(self):
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()

        self.assertEqual(
            config.database_url,
            "postgresql://postgres:postgres@127.0.0.1:5432/culture_media",
        )
        self.assertEqual(
            config.frontend_origins,
            ["http://localhost:5173", "http://127.0.0.1:5173"],
        )

    def test_load_config_reads_backend_env_file(self):
        env_path = Path("backend/.env")

        def fake_load_dotenv(path, override=False):
            if path == env_path and not override:
                os.environ["LLM_API_KEY"] = "from-env-file"
                os.environ["LLM_BASE_URL"] = "https://model.example.com/v1"
                os.environ["LLM_MODEL"] = "demo-model"
                return True
            return False

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(config_module, "ENV_FILE", env_path, create=True),
            patch.object(config_module, "load_dotenv", fake_load_dotenv, create=True),
        ):
            config = load_config()

        self.assertEqual(config.llm_api_key, "from-env-file")
        self.assertEqual(config.llm_base_url, "https://model.example.com/v1")
        self.assertEqual(config.llm_model, "demo-model")

    def test_usage_protection_config_reads_environment_values(self):
        with patch.dict(
            os.environ,
            {
                "API_RATE_LIMIT_PER_MINUTE": "5",
                "LLM_DAILY_REQUEST_WARNING_LIMIT": "50",
                "API_USAGE_LOG_PATH": "logs/demo-usage.jsonl",
            },
            clear=True,
        ):
            config = load_config()

        self.assertEqual(config.api_rate_limit_per_minute, 5)
        self.assertEqual(config.llm_daily_request_warning_limit, 50)
        self.assertEqual(config.api_usage_log_path, "logs/demo-usage.jsonl")

    def test_frontend_origins_reads_comma_separated_environment_value(self):
        with patch.dict(
            os.environ,
            {
                "FRONTEND_ORIGINS": (
                    "http://localhost:5173/demo-path, "
                    "http://127.0.0.1:5173"
                ),
            },
            clear=True,
        ):
            config = load_config()

        self.assertEqual(
            config.frontend_origins,
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ],
        )


if __name__ == "__main__":
    unittest.main()
