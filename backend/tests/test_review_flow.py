import asyncio
import unittest

from app.core.domain import (
    PLATFORM_GOOGLE,
    PLATFORM_XIAOHONGSHU,
    RequestValidationError,
    build_review_prompt,
    validate_generation_input,
)
from app.services.review_service import generate_review, notify_wecom, process_incoming_review


class FakeLlmClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []
        self.max_tokens = []

    async def complete(self, prompt, max_tokens=None):
        self.prompts.append(prompt)
        self.max_tokens.append(max_tokens)
        return self.responses.pop(0)


class FakeWeComClient:
    def __init__(self, sent=True):
        self.sent = sent
        self.messages = []

    async def send_markdown(self, message):
        self.messages.append(message)
        return self.sent


class FakeReviewRepository:
    def __init__(self):
        self.records = []

    async def save(self, record):
        self.records.append(record)
        return len(self.records)


class ReviewFlowTests(unittest.TestCase):
    def test_generation_input_requires_one_or_two_feelings(self):
        with self.assertRaisesRegex(RequestValidationError, "Choose 1-2 feelings"):
            validate_generation_input([], PLATFORM_GOOGLE)

        with self.assertRaisesRegex(RequestValidationError, "Choose 1-2 feelings"):
            validate_generation_input(["服务好", "出餐快", "环境干净"], PLATFORM_GOOGLE)

    def test_generation_input_rejects_unknown_platform(self):
        with self.assertRaisesRegex(RequestValidationError, "Unsupported platform"):
            validate_generation_input(["服务好"], "instagram")

    def test_google_prompt_targets_north_american_english_review_style(self):
        prompt = build_review_prompt(["服务好", "环境干净"], PLATFORM_GOOGLE)

        self.assertIn("Sunny Tea House", prompt)
        self.assertIn("English", prompt)
        self.assertIn("North American", prompt)
        self.assertIn("objective", prompt)
        self.assertIn("45-75 English words", prompt)
        self.assertIn("under 420 characters", prompt)
        self.assertIn("服务好, 环境干净", prompt)

    def test_xiaohongshu_prompt_targets_chinese_seed_note_style(self):
        prompt = build_review_prompt(["饮品颜值高"], PLATFORM_XIAOHONGSHU)

        self.assertIn("小红书", prompt)
        self.assertIn("推荐文案", prompt)
        self.assertIn("中文", prompt)
        self.assertIn("Emoji", prompt)
        self.assertIn("呼吸感", prompt)
        self.assertIn("80-140 个中文字符", prompt)
        self.assertIn("不超过 220 个中文字符", prompt)
        self.assertIn("饮品颜值高", prompt)

    def test_generate_review_returns_llm_text_and_platform(self):
        llm = FakeLlmClient([" Great service and a clean space. "])

        result = asyncio.run(generate_review(["服务好"], PLATFORM_GOOGLE, llm))

        self.assertEqual(
            result,
            {"text": "Great service and a clean space.", "platform": PLATFORM_GOOGLE},
        )
        self.assertIn("Google", llm.prompts[0])
        self.assertEqual(llm.max_tokens, [140])

    def test_generate_review_retries_once_when_model_returns_empty_text(self):
        llm = FakeLlmClient(["   ", " Great service and a clean space. "])

        result = asyncio.run(generate_review(["服务好"], PLATFORM_GOOGLE, llm))

        self.assertEqual(
            result,
            {"text": "Great service and a clean space.", "platform": PLATFORM_GOOGLE},
        )
        self.assertEqual(llm.max_tokens, [140, 560])

    def test_generate_xiaohongshu_uses_short_completion_budget(self):
        llm = FakeLlmClient([" 今天喝到一杯很清爽的奶茶，出餐快，颜值也在线～ "])

        result = asyncio.run(generate_review(["出餐快"], PLATFORM_XIAOHONGSHU, llm))

        self.assertEqual(result["platform"], PLATFORM_XIAOHONGSHU)
        self.assertEqual(llm.max_tokens, [180])

    def test_notify_wecom_sends_summary_and_reply_draft(self):
        llm = FakeLlmClient(
            [
                "中文摘要：顾客喜欢服务和环境。\n商家回复草稿：感谢您的喜欢，欢迎再来。",
            ]
        )
        wecom = FakeWeComClient(sent=True)

        result = asyncio.run(
            notify_wecom(
                review="Loved the service and clean space.",
                platform=PLATFORM_GOOGLE,
                feelings=["服务好", "环境干净"],
                llm_client=llm,
                wecom_client=wecom,
            )
        )

        self.assertEqual(result["summary"], "顾客喜欢服务和环境。")
        self.assertEqual(result["replyDraft"], "感谢您的喜欢，欢迎再来。")
        self.assertTrue(result["sent"])
        self.assertEqual(len(wecom.messages), 1)
        self.assertIn("顾客喜欢服务和环境", wecom.messages[0])
        self.assertIn("感谢您的喜欢", wecom.messages[0])

    def test_notify_wecom_reports_send_failure_without_losing_generated_copy(self):
        llm = FakeLlmClient(["摘要：顾客认可出餐速度。\n回复：谢谢反馈，我们会继续保持。"])
        wecom = FakeWeComClient(sent=False)

        result = asyncio.run(
            notify_wecom(
                review="出餐很快，饮品也好看。",
                platform=PLATFORM_XIAOHONGSHU,
                feelings=["出餐快", "饮品颜值高"],
                llm_client=llm,
                wecom_client=wecom,
            )
        )

        self.assertFalse(result["sent"])
        self.assertEqual(result["summary"], "顾客认可出餐速度。")
        self.assertEqual(result["replyDraft"], "谢谢反馈，我们会继续保持。")

    def test_notify_wecom_persists_generated_review_when_repository_is_supplied(self):
        llm = FakeLlmClient(["中文摘要：顾客认可服务。\n商家回复草稿：谢谢认可，欢迎再来。"])
        wecom = FakeWeComClient(sent=True)
        repository = FakeReviewRepository()

        result = asyncio.run(
            notify_wecom(
                review="The staff was very kind.",
                platform=PLATFORM_GOOGLE,
                feelings=["服务好"],
                llm_client=llm,
                wecom_client=wecom,
                review_repository=repository,
            )
        )

        self.assertEqual(result["id"], 1)
        self.assertEqual(len(repository.records), 1)
        record = repository.records[0]
        self.assertEqual(record.source, "generated")
        self.assertEqual(record.platform, PLATFORM_GOOGLE)
        self.assertEqual(record.review_text, "The staff was very kind.")
        self.assertEqual(record.feelings, ["服务好"])
        self.assertEqual(record.summary, "顾客认可服务。")
        self.assertEqual(record.reply_draft, "谢谢认可，欢迎再来。")
        self.assertTrue(record.wecom_sent)

    def test_process_incoming_review_analyzes_pushes_and_persists_review(self):
        llm = FakeLlmClient(["中文摘要：顾客喜欢饮品和服务。\n商家回复草稿：感谢您的支持，欢迎下次再来。"])
        wecom = FakeWeComClient(sent=True)
        repository = FakeReviewRepository()

        result = asyncio.run(
            process_incoming_review(
                review="Milk tea tasted great and the team was friendly.",
                platform=PLATFORM_GOOGLE,
                llm_client=llm,
                wecom_client=wecom,
                review_repository=repository,
                external_review_id="google-001",
                author="Alice",
                rating=5,
                feelings=[],
            )
        )

        self.assertEqual(result["id"], 1)
        self.assertTrue(result["sent"])
        self.assertEqual(result["summary"], "顾客喜欢饮品和服务。")
        self.assertEqual(result["replyDraft"], "感谢您的支持，欢迎下次再来。")
        self.assertEqual(len(wecom.messages), 1)
        self.assertIn("Alice", wecom.messages[0])
        self.assertIn("5", wecom.messages[0])
        record = repository.records[0]
        self.assertEqual(record.source, "incoming")
        self.assertEqual(record.external_review_id, "google-001")
        self.assertEqual(record.author, "Alice")
        self.assertEqual(record.rating, 5)
        self.assertEqual(record.feelings, [])


if __name__ == "__main__":
    unittest.main()
