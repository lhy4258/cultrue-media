from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import AppConfig, load_config
from app.core.domain import RequestValidationError
from app.core.usage_guard import ModelUsageGuard, UsageDecision
from app.integrations.llm import OpenAICompatibleClient
from app.integrations.wecom import WeComWebhookClient
from app.repositories.reviews import PostgresReviewRepository
from app.services.review_service import generate_review, notify_wecom, process_incoming_review


class GenerateReviewRequest(BaseModel):
    feelings: list[str] = Field(min_length=1, max_length=2)
    platform: str


class NotifyWeComRequest(BaseModel):
    review: str = Field(min_length=1)
    platform: str
    feelings: list[str] = Field(min_length=1, max_length=2)


class IncomingReviewRequest(BaseModel):
    review: str = Field(min_length=1)
    platform: str
    reviewId: str | None = None
    author: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    feelings: list[str] = Field(default_factory=list, max_length=2)


router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)
_usage_guard: ModelUsageGuard | None = None
_usage_guard_signature: tuple[int, int, str] | None = None


@router.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@router.post("/generate-review")
async def generate_review_endpoint(payload: GenerateReviewRequest, request: Request) -> dict[str, str]:
    config = load_config()
    usage = _begin_model_request(
        config=config,
        request=request,
        endpoint="/api/generate-review",
        platform=payload.platform,
        feelings_count=len(payload.feelings),
    )
    llm_client = OpenAICompatibleClient(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
        model=config.llm_model,
        timeout_seconds=config.llm_timeout_seconds,
    )
    try:
        result = await generate_review(payload.feelings, payload.platform, llm_client)
        _finish_model_request(usage, success=True, status_code=200)
        return result
    except RequestValidationError as exc:
        _finish_model_request(usage, success=False, status_code=400, error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        _finish_model_request(usage, success=False, status_code=502, error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/notify-wecom")
async def notify_wecom_endpoint(payload: NotifyWeComRequest, request: Request) -> dict[str, str | bool | int]:
    config = load_config()
    usage = _begin_model_request(
        config=config,
        request=request,
        endpoint="/api/notify-wecom",
        platform=payload.platform,
        feelings_count=len(payload.feelings),
    )
    llm_client = OpenAICompatibleClient(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
        model=config.llm_model,
        timeout_seconds=config.llm_timeout_seconds,
    )
    wecom_client = WeComWebhookClient(webhook_url=config.wecom_webhook_url)
    review_repository = PostgresReviewRepository(database_url=config.database_url)
    try:
        result = await notify_wecom(
            review=payload.review,
            platform=payload.platform,
            feelings=payload.feelings,
            llm_client=llm_client,
            wecom_client=wecom_client,
            review_repository=review_repository,
        )
        _finish_model_request(usage, success=True, status_code=200)
        return result
    except RequestValidationError as exc:
        _finish_model_request(usage, success=False, status_code=400, error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        _finish_model_request(usage, success=False, status_code=502, error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/incoming-review")
async def incoming_review_endpoint(payload: IncomingReviewRequest, request: Request) -> dict[str, str | bool | int]:
    config = load_config()
    usage = _begin_model_request(
        config=config,
        request=request,
        endpoint="/api/incoming-review",
        platform=payload.platform,
        feelings_count=len(payload.feelings),
    )
    llm_client = OpenAICompatibleClient(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
        model=config.llm_model,
        timeout_seconds=config.llm_timeout_seconds,
    )
    wecom_client = WeComWebhookClient(webhook_url=config.wecom_webhook_url)
    review_repository = PostgresReviewRepository(database_url=config.database_url)
    try:
        result = await process_incoming_review(
            review=payload.review,
            platform=payload.platform,
            llm_client=llm_client,
            wecom_client=wecom_client,
            review_repository=review_repository,
            external_review_id=payload.reviewId,
            author=payload.author,
            rating=payload.rating,
            feelings=payload.feelings,
        )
        _finish_model_request(usage, success=True, status_code=200)
        return result
    except RequestValidationError as exc:
        _finish_model_request(usage, success=False, status_code=400, error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        _finish_model_request(usage, success=False, status_code=502, error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _begin_model_request(
    *,
    config: AppConfig,
    request: Request,
    endpoint: str,
    platform: str,
    feelings_count: int,
) -> UsageDecision:
    guard = _get_usage_guard(config)
    decision = guard.begin_request(
        endpoint=endpoint,
        client_id=_client_id(request),
        platform=platform,
        feelings_count=feelings_count,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail="请求太频繁，请稍后再试。",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )
    if decision.cost_warning:
        logger.warning(
            "LLM daily request warning active: %s/%s",
            decision.daily_count,
            config.llm_daily_request_warning_limit,
        )
    return decision


def _finish_model_request(
    decision: UsageDecision,
    *,
    success: bool,
    status_code: int,
    error: str = "",
) -> None:
    _get_usage_guard(load_config()).finish_request(
        decision,
        success=success,
        status_code=status_code,
        error=error,
    )


def _get_usage_guard(config: AppConfig) -> ModelUsageGuard:
    global _usage_guard
    global _usage_guard_signature

    signature = (
        config.api_rate_limit_per_minute,
        config.llm_daily_request_warning_limit,
        config.api_usage_log_path,
    )
    if _usage_guard is None or _usage_guard_signature != signature:
        _usage_guard = ModelUsageGuard(
            rate_limit_per_minute=config.api_rate_limit_per_minute,
            daily_warning_limit=config.llm_daily_request_warning_limit,
            log_path=config.api_usage_log_path,
        )
        _usage_guard_signature = signature
    return _usage_guard


def _client_id(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host
