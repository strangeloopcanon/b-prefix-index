from __future__ import annotations

import argparse
from collections.abc import Iterable
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .api import build_api
from .models import PrefixEvent, PrefixIndexConfig, PrefixRecommendation

EventsPayload = Annotated[list[PrefixEvent], Field(min_length=1)]


class IngestRequest(BaseModel):
    """Payload for ingesting prefix events."""

    events: EventsPayload


class IngestResponse(BaseModel):
    """Response returned after successful ingestion."""

    ingested: int


def create_app(
    config: PrefixIndexConfig | None = None, *, cors_origins: Iterable[str] | None = None
) -> FastAPI:
    """Construct a FastAPI app backed by PrefixIndexAPI."""

    api = build_api(config)
    app = FastAPI(title="Offline Prefix Index", version="0.1.0")
    app.state.api = api

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/healthz", status_code=status.HTTP_200_OK)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
    def ingest(payload: IngestRequest) -> IngestResponse:
        app.state.api.ingest_events(payload.events)
        return IngestResponse(ingested=len(payload.events))

    @app.get("/suggest", response_model=list[PrefixRecommendation])
    def suggest(
        top_k: int | None = Query(default=None, ge=1, le=10_000),
        min_score: float | None = Query(default=None, ge=0.0),
    ) -> list[PrefixRecommendation]:
        return app.state.api.recommendations(top_k=top_k, min_score=min_score)

    @app.get("/snapshot", response_model=list[PrefixRecommendation])
    def snapshot() -> list[PrefixRecommendation]:
        stats = app.state.api.snapshot()
        return [
            PrefixRecommendation(
                prefix_id=stat.prefix_id,
                tenant=stat.tenant,
                model_id=stat.model_id,
                score=stat.score,
                hint=f"hits={stat.hit_count} bytes={stat.total_bytes} last_seen={stat.last_seen_ms}",
            )
            for stat in stats
        ]

    return app


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the offline prefix index HTTP service.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8000, help="TCP port for the service.")
    parser.add_argument(
        "--store", type=str, default=None, help="Optional JSONL store path for persistence."
    )
    parser.add_argument(
        "--decay-half-life-ms",
        type=int,
        default=3_600_000,
        help="Half-life used for exponential decay of prefix scores.",
    )
    parser.add_argument(
        "--max-recs", type=int, default=100, help="Default maximum number of suggestions."
    )
    parser.add_argument(
        "--min-score", type=float, default=0.0, help="Minimum default score filter."
    )
    parser.add_argument(
        "--cors-origin",
        action="append",
        dest="cors_origins",
        default=None,
        help="Optional CORS origin (repeatable).",
    )
    args = parser.parse_args(argv)

    config = PrefixIndexConfig(
        decay_half_life_ms=args.decay_half_life_ms,
        max_recommendations=args.max_recs,
        min_score=args.min_score,
        store_path=args.store,
    )
    app = create_app(config=config, cors_origins=args.cors_origins)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


app = create_app()
