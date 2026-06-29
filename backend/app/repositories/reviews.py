from __future__ import annotations

import asyncio

from psycopg.types.json import Jsonb

from app.core.domain import ReviewRecord


CREATE_REVIEWS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reviews (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    platform TEXT NOT NULL,
    external_review_id TEXT,
    author TEXT,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    feelings JSONB NOT NULL DEFAULT '[]'::jsonb,
    review_text TEXT NOT NULL,
    summary TEXT NOT NULL,
    reply_draft TEXT NOT NULL,
    wecom_sent BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviews_platform_created_at
    ON reviews (platform, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reviews_external_review_id
    ON reviews (external_review_id)
    WHERE external_review_id IS NOT NULL;
"""


INSERT_REVIEW_SQL = """
INSERT INTO reviews (
    source,
    platform,
    external_review_id,
    author,
    rating,
    feelings,
    review_text,
    summary,
    reply_draft,
    wecom_sent
) VALUES (
    %(source)s,
    %(platform)s,
    %(external_review_id)s,
    %(author)s,
    %(rating)s,
    %(feelings)s,
    %(review_text)s,
    %(summary)s,
    %(reply_draft)s,
    %(wecom_sent)s
)
RETURNING id;
"""


class PostgresReviewRepository:
    def __init__(self, *, database_url: str) -> None:
        self.database_url = database_url

    async def ensure_schema(self) -> None:
        await asyncio.to_thread(_ensure_schema, self.database_url)

    async def save(self, record: ReviewRecord) -> int:
        return await asyncio.to_thread(_save, self.database_url, record)


def _ensure_schema(database_url: str) -> None:
    import psycopg

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_REVIEWS_TABLE_SQL)
        connection.commit()


def _save(database_url: str, record: ReviewRecord) -> int:
    import psycopg

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                INSERT_REVIEW_SQL,
                {
                    "source": record.source,
                    "platform": record.platform,
                    "external_review_id": record.external_review_id,
                    "author": record.author,
                    "rating": record.rating,
                    "feelings": Jsonb(record.feelings),
                    "review_text": record.review_text,
                    "summary": record.summary,
                    "reply_draft": record.reply_draft,
                    "wecom_sent": record.wecom_sent,
                },
            )
            row = cursor.fetchone()
        connection.commit()

    if row is None:
        raise RuntimeError("Failed to save review")
    return int(row[0])
