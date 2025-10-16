"""Typed data models used across the prefix indexer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PrefixEvent(BaseModel):
    """Single KV cache access trace."""

    prefix_id: str = Field(..., min_length=1)
    tenant: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)
    layer: int = Field(..., ge=0)
    page_start: int = Field(..., ge=0)
    page_end: int = Field(..., ge=0)
    bytes: int = Field(..., ge=0)
    latency_ms: float = Field(..., ge=0.0)
    timestamp_ms: int = Field(..., ge=0)

    @property
    def page_span(self) -> int:
        """Number of pages touched by the event."""
        return max(0, self.page_end - self.page_start + 1)


class PrefixStats(BaseModel):
    """Aggregated statistics for a prefix within a tenant."""

    prefix_id: str
    tenant: str
    model_id: str
    hit_count: int = Field(..., ge=0)
    total_bytes: int = Field(..., ge=0)
    avg_latency_ms: float = Field(..., ge=0.0)
    score: float = Field(..., ge=0.0)
    last_seen_ms: int = Field(..., ge=0)


class PrefixRecommendation(BaseModel):
    """Recommendation produced for planners."""

    prefix_id: str
    tenant: str
    model_id: str
    score: float
    hint: str


class PrefixIndexConfig(BaseModel):
    """Runtime configuration switches."""

    decay_half_life_ms: int = Field(3_600_000, ge=1)
    max_recommendations: int = Field(100, ge=1)
    min_score: float = Field(0.0, ge=0.0)
    store_path: str | None = None
