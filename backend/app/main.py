from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import load_config
from app.repositories.reviews import PostgresReviewRepository


logger = logging.getLogger(__name__)
config = load_config()
app = FastAPI(title="Sunny Tea House AI Review Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.on_event("startup")
async def ensure_database_schema() -> None:
    try:
        await PostgresReviewRepository(database_url=config.database_url).ensure_schema()
    except Exception as exc:
        logger.warning("Database schema initialization skipped: %s", exc)


app.include_router(router)
