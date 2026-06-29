from __future__ import annotations

from dataclasses import dataclass


PLATFORM_GOOGLE = "google"
PLATFORM_XIAOHONGSHU = "xiaohongshu"
SUPPORTED_PLATFORMS = {PLATFORM_GOOGLE, PLATFORM_XIAOHONGSHU}
GOOGLE_GENERATION_MAX_TOKENS = 140
XIAOHONGSHU_GENERATION_MAX_TOKENS = 180


class RequestValidationError(ValueError):
    """Raised when a client request cannot be fulfilled."""


@dataclass(frozen=True)
class WeComAnalysis:
    summary: str
    reply_draft: str


@dataclass(frozen=True)
class ReviewRecord:
    source: str
    platform: str
    review_text: str
    feelings: list[str]
    summary: str
    reply_draft: str
    wecom_sent: bool
    external_review_id: str | None = None
    author: str | None = None
    rating: int | None = None


def validate_platform(platform: str) -> str:
    if platform not in SUPPORTED_PLATFORMS:
        raise RequestValidationError("Unsupported platform")
    return platform


def normalize_optional_feelings(feelings: list[str]) -> list[str]:
    normalized = [item.strip() for item in feelings if isinstance(item, str) and item.strip()]
    if len(normalized) > 2:
        raise RequestValidationError("Choose 1-2 feelings")
    return normalized


def validate_generation_input(feelings: list[str], platform: str) -> list[str]:
    validate_platform(platform)
    normalized = normalize_optional_feelings(feelings)
    if len(normalized) < 1 or len(normalized) > 2:
        raise RequestValidationError("Choose 1-2 feelings")

    return normalized


def validate_review_text(review: str) -> str:
    text = review.strip()
    if not text:
        raise RequestValidationError("Review is required")
    return text


def get_generation_max_tokens(platform: str) -> int:
    validate_platform(platform)
    if platform == PLATFORM_GOOGLE:
        return GOOGLE_GENERATION_MAX_TOKENS
    return XIAOHONGSHU_GENERATION_MAX_TOKENS


def build_review_prompt(feelings: list[str], platform: str) -> str:
    normalized = validate_generation_input(feelings, platform)
    feeling_text = ", ".join(normalized)

    if platform == PLATFORM_GOOGLE:
        return f"""
You are helping a real customer write a Google review for Sunny Tea House, a milk tea shop in San Jose.

Customer feelings: {feeling_text}

Write one concise English review in a natural North American consumer voice.
Keep it within 45-75 English words and under 420 characters.
The tone must be objective, specific, warm, and not overly promotional.
Do not mention AI, prompts, discounts, or instructions.
Return only the review text.
""".strip()

    return f"""
你正在帮助顾客为 San Jose 的奶茶店 Sunny Tea House 写一篇小红书推荐文案。

顾客选择的消费感受：{feeling_text}

请用中文输出，语气真实自然，带一点生活感和分享欲。
要求包含适当的 Emoji，段落之间有呼吸感，像真实用户发布的小红书笔记。
正文控制在 80-140 个中文字符，最多 2-3 个短段落，不超过 220 个中文字符。
不要提到 AI、提示词、任务要求或系统说明。
只返回可发布正文。
""".strip()


def build_wecom_prompt(review: str, platform: str, feelings: list[str]) -> str:
    normalized = validate_generation_input(feelings, platform)
    return f"""
请阅读顾客刚生成的评价，并给 Sunny Tea House 商家输出两部分内容。

发布平台：{platform}
顾客感受：{", ".join(normalized)}
评价正文：
{review.strip()}

请严格按以下格式返回两行：
中文摘要：用一句中文概括顾客主要反馈
商家回复草稿：用一句亲切、专业、不夸张的中文回复顾客
""".strip()


def build_incoming_review_prompt(
    *,
    review: str,
    platform: str,
    author: str | None = None,
    rating: int | None = None,
    feelings: list[str] | None = None,
) -> str:
    validate_platform(platform)
    review_text = validate_review_text(review)
    normalized_feelings = normalize_optional_feelings(feelings or [])
    feeling_line = "、".join(normalized_feelings) if normalized_feelings else "未提供"
    author_line = author.strip() if author and author.strip() else "未提供"
    rating_line = str(rating) if rating is not None else "未提供"
    platform_name = "Google" if platform == PLATFORM_GOOGLE else "小红书"

    return f"""
请阅读 Sunny Tea House 刚收到的一条新顾客评论，并输出给商家看的处理信息。

发布平台：{platform_name}
顾客昵称：{author_line}
评分：{rating_line}
感受标签：{feeling_line}
评论正文：
{review_text}

请严格按以下格式返回两行：
中文摘要：用一句中文概括顾客主要反馈
商家回复草稿：用一句亲切、专业、不夸张的中文回复顾客
""".strip()


def parse_wecom_analysis(text: str) -> WeComAnalysis:
    summary = ""
    reply_draft = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("中文摘要："):
            summary = line.removeprefix("中文摘要：").strip()
        elif line.startswith("摘要："):
            summary = line.removeprefix("摘要：").strip()
        elif line.startswith("商家回复草稿："):
            reply_draft = line.removeprefix("商家回复草稿：").strip()
        elif line.startswith("回复："):
            reply_draft = line.removeprefix("回复：").strip()

    if not summary or not reply_draft:
        parts = [part.strip() for part in text.splitlines() if part.strip()]
        if not summary and parts:
            summary = parts[0]
        if not reply_draft and len(parts) > 1:
            reply_draft = parts[1]

    return WeComAnalysis(summary=summary, reply_draft=reply_draft)


def format_wecom_markdown(
    *,
    review: str,
    platform: str,
    feelings: list[str],
    summary: str,
    reply_draft: str,
) -> str:
    feeling_text = "、".join(validate_generation_input(feelings, platform))
    platform_name = "Google" if platform == PLATFORM_GOOGLE else "小红书"
    return "\n".join(
        [
            "## Sunny Tea House 新评价提醒",
            f"> 平台：{platform_name}",
            f"> 感受：{feeling_text}",
            "",
            f"**中文摘要**：{summary}",
            "",
            f"**商家回复草稿**：{reply_draft}",
            "",
            "**顾客评价原文**",
            review.strip(),
        ]
    )


def format_incoming_review_markdown(
    *,
    review: str,
    platform: str,
    summary: str,
    reply_draft: str,
    external_review_id: str | None = None,
    author: str | None = None,
    rating: int | None = None,
    feelings: list[str] | None = None,
) -> str:
    validate_platform(platform)
    platform_name = "Google" if platform == PLATFORM_GOOGLE else "小红书"
    normalized_feelings = normalize_optional_feelings(feelings or [])
    lines = [
        "## Sunny Tea House 新评论提醒",
        f"> 平台：{platform_name}",
    ]

    if external_review_id:
        lines.append(f"> 评论 ID：{external_review_id}")
    if author:
        lines.append(f"> 顾客：{author}")
    if rating is not None:
        lines.append(f"> 评分：{rating}")
    if normalized_feelings:
        lines.append(f"> 感受：{'、'.join(normalized_feelings)}")

    lines.extend(
        [
            "",
            f"**中文摘要**：{summary}",
            "",
            f"**商家回复草稿**：{reply_draft}",
            "",
            "**顾客评论原文**",
            validate_review_text(review),
        ]
    )
    return "\n".join(lines)
