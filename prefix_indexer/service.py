"""Service orchestrating ingestion, aggregation, and recommendations."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .analytics import aggregate_events, merge_stats
from .models import PrefixEvent, PrefixIndexConfig, PrefixRecommendation, PrefixStats
from .storage import PrefixIndexStore, create_store


class PrefixIndexService:
    """Coordinates the offline prefix index lifecycle."""

    def __init__(self, config: PrefixIndexConfig, store: PrefixIndexStore | None = None) -> None:
        self.config = config
        self.store = store or create_store(config)
        self.store.load()

    def ingest_events(self, events: Iterable[PrefixEvent], *, now_ms: int | None = None) -> None:
        """Aggregate raw events and merge them into the current index."""
        updates = aggregate_events(
            events, now_ms=now_ms, half_life_ms=self.config.decay_half_life_ms
        )
        existing = self.store.list_stats()
        merged = merge_stats(
            existing,
            updates.values(),
            half_life_ms=self.config.decay_half_life_ms,
        )
        self.store.bulk_upsert(merged.values())

    def ingest_jsonl(self, path: Path, *, now_ms: int | None = None) -> None:
        """Read JSONL trace file and ingest."""
        with path.open("r", encoding="utf-8") as fh:
            events = [PrefixEvent.model_validate_json(line) for line in fh if line.strip()]
        self.ingest_events(events, now_ms=now_ms)

    def recommendations(
        self,
        *,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> list[PrefixRecommendation]:
        """Return ranked prefix recommendations."""
        limit = top_k if top_k is not None else self.config.max_recommendations
        score_floor = min_score if min_score is not None else self.config.min_score
        stats = sorted(
            self.store.list_stats(),
            key=lambda s: (s.score, s.hit_count, s.last_seen_ms),
            reverse=True,
        )
        recs: list[PrefixRecommendation] = []
        for stat in stats:
            if stat.score < score_floor:
                continue
            hint = (
                f"score={stat.score:.1f} hits={stat.hit_count} "
                f"bytes={stat.total_bytes} last_seen={stat.last_seen_ms}"
            )
            recs.append(
                PrefixRecommendation(
                    prefix_id=stat.prefix_id,
                    tenant=stat.tenant,
                    model_id=stat.model_id,
                    score=stat.score,
                    hint=hint,
                )
            )
            if len(recs) >= limit:
                break
        return recs

    def export_snapshot(self) -> list[PrefixStats]:
        """Return all stats, useful for tests or diagnostics."""
        return self.store.list_stats()

    def dump_json(self) -> str:
        """Serialize the current index to JSON for callers that need a blob."""
        payload = [stat.model_dump() for stat in self.store.list_stats()]
        return json.dumps(payload, indent=2)
