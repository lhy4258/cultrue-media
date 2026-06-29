from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Callable


logger = logging.getLogger(__name__)

LogWriter = Callable[[dict], None]


@dataclass(frozen=True)
class UsageDecision:
    request_id: str
    allowed: bool
    retry_after_seconds: int
    daily_count: int
    cost_warning: bool


class ModelUsageGuard:
    def __init__(
        self,
        *,
        rate_limit_per_minute: int,
        daily_warning_limit: int,
        log_path: str,
        clock: Callable[[], float] | None = None,
        log_writer: LogWriter | None = None,
    ) -> None:
        self.rate_limit_per_minute = max(0, rate_limit_per_minute)
        self.daily_warning_limit = max(0, daily_warning_limit)
        self.log_path = Path(log_path) if log_path else None
        self.clock = clock or time.time
        self.log_writer = log_writer
        self._requests_by_client: dict[str, deque[float]] = defaultdict(deque)
        self._daily_counts: dict[str, int] = defaultdict(int)
        self._alerted_dates: set[str] = set()
        self._lock = Lock()

    def begin_request(
        self,
        *,
        endpoint: str,
        client_id: str,
        platform: str,
        feelings_count: int,
    ) -> UsageDecision:
        now = self.clock()
        request_id = uuid.uuid4().hex
        client_key = _hash_client_id(client_id)

        with self._lock:
            bucket = self._requests_by_client[client_key]
            while bucket and now - bucket[0] >= 60:
                bucket.popleft()

            if self.rate_limit_per_minute and len(bucket) >= self.rate_limit_per_minute:
                retry_after = max(1, int(60 - (now - bucket[0])))
                decision = UsageDecision(
                    request_id=request_id,
                    allowed=False,
                    retry_after_seconds=retry_after,
                    daily_count=self._daily_counts[_date_key(now)],
                    cost_warning=False,
                )
                self._write_event(
                    {
                        "event": "model_request_rate_limited",
                        "requestId": decision.request_id,
                        "endpoint": endpoint,
                        "client": client_key,
                        "platform": platform,
                        "feelingsCount": feelings_count,
                        "rateLimitPerMinute": self.rate_limit_per_minute,
                        "retryAfterSeconds": decision.retry_after_seconds,
                        "timestamp": _iso_timestamp(now),
                    }
                )
                return decision

            bucket.append(now)
            today = _date_key(now)
            self._daily_counts[today] += 1
            daily_count = self._daily_counts[today]
            cost_warning = self.daily_warning_limit > 0 and daily_count >= self.daily_warning_limit
            decision = UsageDecision(
                request_id=request_id,
                allowed=True,
                retry_after_seconds=0,
                daily_count=daily_count,
                cost_warning=cost_warning,
            )
            self._write_event(
                {
                    "event": "model_request_started",
                    "requestId": decision.request_id,
                    "endpoint": endpoint,
                    "client": client_key,
                    "platform": platform,
                    "feelingsCount": feelings_count,
                    "dailyCount": daily_count,
                    "dailyWarningLimit": self.daily_warning_limit,
                    "costWarning": cost_warning,
                    "timestamp": _iso_timestamp(now),
                }
            )
            if cost_warning and today not in self._alerted_dates:
                self._alerted_dates.add(today)
                self._write_event(
                    {
                        "event": "model_cost_warning",
                        "date": today,
                        "dailyCount": daily_count,
                        "dailyWarningLimit": self.daily_warning_limit,
                        "timestamp": _iso_timestamp(now),
                    }
                )
                logger.warning(
                    "LLM daily request warning reached: %s/%s",
                    daily_count,
                    self.daily_warning_limit,
                )

        return decision

    def finish_request(
        self,
        decision: UsageDecision,
        *,
        success: bool,
        status_code: int,
        error: str = "",
    ) -> None:
        if not decision.allowed:
            return

        event = {
            "event": "model_request_finished",
            "requestId": decision.request_id,
            "success": success,
            "statusCode": status_code,
            "timestamp": _iso_timestamp(self.clock()),
        }
        if error:
            event["error"] = error[:300]
        self._write_event(event)

    def _write_event(self, event: dict) -> None:
        if self.log_writer is not None:
            self.log_writer(event)
            return
        if self.log_path is None:
            return

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("Failed to write API usage log: %s", exc)


def _hash_client_id(client_id: str) -> str:
    normalized = client_id.strip() or "unknown"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _date_key(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()


def _iso_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
