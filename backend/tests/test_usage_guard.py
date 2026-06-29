import unittest

from app.core.usage_guard import ModelUsageGuard


class UsageGuardTests(unittest.TestCase):
    def test_rate_limit_blocks_extra_requests_and_logs_without_review_text(self):
        now = 1_700_000_000.0
        events = []
        guard = ModelUsageGuard(
            rate_limit_per_minute=2,
            daily_warning_limit=100,
            log_path="",
            clock=lambda: now,
            log_writer=events.append,
        )

        first = guard.begin_request(
            endpoint="/api/generate-review",
            client_id="127.0.0.1",
            platform="google",
            feelings_count=1,
        )
        second = guard.begin_request(
            endpoint="/api/generate-review",
            client_id="127.0.0.1",
            platform="google",
            feelings_count=1,
        )
        third = guard.begin_request(
            endpoint="/api/generate-review",
            client_id="127.0.0.1",
            platform="google",
            feelings_count=1,
        )

        self.assertTrue(first.allowed)
        self.assertTrue(second.allowed)
        self.assertFalse(third.allowed)
        self.assertGreater(third.retry_after_seconds, 0)
        self.assertEqual(events[-1]["event"], "model_request_rate_limited")
        self.assertNotIn("The staff was friendly", str(events))

    def test_finish_request_logs_result_status(self):
        events = []
        guard = ModelUsageGuard(
            rate_limit_per_minute=10,
            daily_warning_limit=100,
            log_path="",
            clock=lambda: 1_700_000_000.0,
            log_writer=events.append,
        )

        decision = guard.begin_request(
            endpoint="/api/generate-review",
            client_id="127.0.0.1",
            platform="xiaohongshu",
            feelings_count=2,
        )
        guard.finish_request(decision, success=False, status_code=502, error="Network error")

        self.assertEqual(events[-1]["event"], "model_request_finished")
        self.assertFalse(events[-1]["success"])
        self.assertEqual(events[-1]["statusCode"], 502)
        self.assertEqual(events[-1]["error"], "Network error")

    def test_daily_warning_event_is_logged_once_when_threshold_is_reached(self):
        events = []
        guard = ModelUsageGuard(
            rate_limit_per_minute=10,
            daily_warning_limit=2,
            log_path="",
            clock=lambda: 1_700_000_000.0,
            log_writer=events.append,
        )

        with self.assertLogs("app.core.usage_guard", level="WARNING"):
            first = guard.begin_request(
                endpoint="/api/generate-review",
                client_id="127.0.0.1",
                platform="google",
                feelings_count=1,
            )
            second = guard.begin_request(
                endpoint="/api/generate-review",
                client_id="127.0.0.2",
                platform="google",
                feelings_count=1,
            )
            third = guard.begin_request(
                endpoint="/api/generate-review",
                client_id="127.0.0.3",
                platform="google",
                feelings_count=1,
            )

        warning_events = [event for event in events if event["event"] == "model_cost_warning"]
        self.assertFalse(first.cost_warning)
        self.assertTrue(second.cost_warning)
        self.assertTrue(third.cost_warning)
        self.assertEqual(len(warning_events), 1)
        self.assertEqual(warning_events[0]["dailyWarningLimit"], 2)


if __name__ == "__main__":
    unittest.main()
