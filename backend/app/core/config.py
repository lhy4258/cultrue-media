from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
BACKEND_DIR = ENV_FILE.parent
DEFAULT_FRONTEND_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


@dataclass(frozen=True)
class AppConfig:
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    llm_timeout_seconds: float
    wecom_webhook_url: str
    database_url: str
    api_rate_limit_per_minute: int
    llm_daily_request_warning_limit: int
    api_usage_log_path: str
    frontend_origins: list[str]


def load_config() -> AppConfig:
    load_dotenv(ENV_FILE, override=False)

    return AppConfig(
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").strip(),
        llm_model=os.getenv("LLM_MODEL", "deepseek-chat").strip(),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        wecom_webhook_url=os.getenv("WECOM_WEBHOOK_URL", "").strip(),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:5432/culture_media",
        ).strip(),
        api_rate_limit_per_minute=_read_int_env("API_RATE_LIMIT_PER_MINUTE", 12),
        llm_daily_request_warning_limit=_read_int_env("LLM_DAILY_REQUEST_WARNING_LIMIT", 100),
        api_usage_log_path=os.getenv(
            "API_USAGE_LOG_PATH",
            str(BACKEND_DIR / "logs" / "api-usage.jsonl"),
        ).strip(),
        frontend_origins=_read_frontend_origins(),
    )


def _read_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _read_frontend_origins() -> list[str]:
    raw_value = os.getenv("FRONTEND_ORIGINS", "").strip()
    if not raw_value:
        return list(DEFAULT_FRONTEND_ORIGINS)

    origins = []
    for item in raw_value.split(","):
        origin = _normalize_origin(item.strip())
        if origin and origin not in origins:
            origins.append(origin)

    return origins or list(DEFAULT_FRONTEND_ORIGINS)


def _normalize_origin(value: str) -> str:
    if not value:
        return ""
    if value == "*":
        return value

    parsed = urlsplit(value)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"

    return value.rstrip("/")
