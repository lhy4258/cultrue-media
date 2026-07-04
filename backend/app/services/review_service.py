from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from app.core.domain import (
    ReviewRecord,
    build_incoming_review_prompt,
    build_review_prompt,
    build_wecom_prompt,
    format_incoming_review_markdown,
    format_wecom_markdown,
    normalize_optional_feelings,
    parse_wecom_analysis,
    validate_platform,
    validate_generation_input,
    validate_review_text,
)


class LlmClient(Protocol):
    async def complete(self, prompt: str) -> str:
        """Return completion text for a prompt."""

    def stream_complete(self, prompt: str) -> AsyncIterator[str]:
        """Return completion text chunks for a prompt."""


class WeComClient(Protocol):
    async def send_markdown(self, message: str) -> bool:
        """Send a markdown message and return whether the provider accepted it."""


class ReviewRepository(Protocol):
    async def save(self, record: ReviewRecord) -> int:
        """Persist a processed review and return its database id."""


async def generate_review(
    feelings: list[str],
    platform: str,
    llm_client: LlmClient,
) -> dict[str, str]:
    normalized = validate_generation_input(feelings, platform)
    prompt = build_review_prompt(normalized, platform)
    text = (await llm_client.complete(prompt)).strip()
    if not text:
        text = (await llm_client.complete(prompt)).strip()
    if not text:
        raise RuntimeError("LLM returned empty completion text")
    return {"text": text, "platform": platform}


def stream_review(
    feelings: list[str],
    platform: str,
    llm_client: LlmClient,
) -> AsyncIterator[str]:
    normalized = validate_generation_input(feelings, platform)
    prompt = build_review_prompt(normalized, platform)
    return llm_client.stream_complete(prompt)


async def notify_wecom(
    *,
    review: str,
    platform: str,
    feelings: list[str],
    llm_client: LlmClient,
    wecom_client: WeComClient,
    review_repository: ReviewRepository | None = None,
) -> dict[str, str | bool | int]:
    normalized = validate_generation_input(feelings, platform)
    review_text = validate_review_text(review)
    analysis_text = await llm_client.complete(build_wecom_prompt(review_text, platform, normalized))
    analysis = parse_wecom_analysis(analysis_text)
    message = format_wecom_markdown(
        review=review_text,
        platform=platform,
        feelings=normalized,
        summary=analysis.summary,
        reply_draft=analysis.reply_draft,
    )
    sent = await wecom_client.send_markdown(message)
    result: dict[str, str | bool | int] = {
        "sent": sent,
        "summary": analysis.summary,
        "replyDraft": analysis.reply_draft,
    }
    if review_repository is not None:
        result["id"] = await review_repository.save(
            ReviewRecord(
                source="generated",
                platform=platform,
                review_text=review_text,
                feelings=normalized,
                summary=analysis.summary,
                reply_draft=analysis.reply_draft,
                wecom_sent=sent,
            )
        )
    return result


async def process_incoming_review(
    *,
    review: str,
    platform: str,
    llm_client: LlmClient,
    wecom_client: WeComClient,
    review_repository: ReviewRepository,
    external_review_id: str | None = None,
    author: str | None = None,
    rating: int | None = None,
    feelings: list[str] | None = None,
) -> dict[str, str | bool | int]:
    validate_platform(platform)
    review_text = validate_review_text(review)
    normalized_feelings = normalize_optional_feelings(feelings or [])

    analysis_text = await llm_client.complete(
        build_incoming_review_prompt(
            review=review_text,
            platform=platform,
            author=author,
            rating=rating,
            feelings=normalized_feelings,
        )
    )
    analysis = parse_wecom_analysis(analysis_text)
    message = format_incoming_review_markdown(
        review=review_text,
        platform=platform,
        summary=analysis.summary,
        reply_draft=analysis.reply_draft,
        external_review_id=external_review_id,
        author=author,
        rating=rating,
        feelings=normalized_feelings,
    )
    sent = await wecom_client.send_markdown(message)
    saved_id = await review_repository.save(
        ReviewRecord(
            source="incoming",
            platform=platform,
            review_text=review_text,
            feelings=normalized_feelings,
            summary=analysis.summary,
            reply_draft=analysis.reply_draft,
            wecom_sent=sent,
            external_review_id=external_review_id,
            author=author,
            rating=rating,
        )
    )
    return {
        "id": saved_id,
        "sent": sent,
        "summary": analysis.summary,
        "replyDraft": analysis.reply_draft,
    }
