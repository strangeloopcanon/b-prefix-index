"""Analytics helpers for offline prefix aggregation."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterable

from .models import PrefixEvent, PrefixStats

PrefixKey = tuple[str, str, str]


def _decay_weight(now_ms: int, timestamp_ms: int, half_life_ms: int) -> float:
    """Return exponential decay weight with configurable half-life."""
    if timestamp_ms > now_ms:
        return 1.0
    elapsed = max(0, now_ms - timestamp_ms)
    if elapsed == 0:
        return 1.0
    return 0.5 ** (elapsed / float(half_life_ms))


def aggregate_events(
    events: Iterable[PrefixEvent],
    *,
    now_ms: int | None = None,
    half_life_ms: int = 3_600_000,
) -> dict[PrefixKey, PrefixStats]:
    """Aggregate raw events into prefix statistics."""
    current_time = now_ms if now_ms is not None else int(time.time() * 1000)
    aggregates: dict[PrefixKey, dict[str, float]] = defaultdict(
        lambda: {
            "hit_count": 0.0,
            "total_bytes": 0.0,
            "latency_sum": 0.0,
            "score": 0.0,
            "last_seen_ms": 0.0,
        }
    )

    for ev in events:
        key: PrefixKey = (ev.prefix_id, ev.tenant, ev.model_id)
        bucket = aggregates[key]
        bucket["hit_count"] += 1.0
        bucket["total_bytes"] += float(ev.bytes)
        bucket["latency_sum"] += float(ev.latency_ms)
        bucket["last_seen_ms"] = max(bucket["last_seen_ms"], float(ev.timestamp_ms))
        weight = _decay_weight(current_time, ev.timestamp_ms, half_life_ms)
        bucket["score"] += weight * float(ev.bytes)

    stats: dict[PrefixKey, PrefixStats] = {}
    for key, bucket in aggregates.items():
        hits = int(bucket["hit_count"])
        total_bytes = int(bucket["total_bytes"])
        avg_latency = bucket["latency_sum"] / hits if hits > 0 else 0.0
        stats[key] = PrefixStats(
            prefix_id=key[0],
            tenant=key[1],
            model_id=key[2],
            hit_count=hits,
            total_bytes=total_bytes,
            avg_latency_ms=avg_latency,
            score=max(bucket["score"], 0.0),
            last_seen_ms=int(bucket["last_seen_ms"]),
        )
    return stats


def merge_stats(
    baseline: Iterable[PrefixStats], updates: Iterable[PrefixStats], *, half_life_ms: int
) -> dict[PrefixKey, PrefixStats]:
    """Merge existing stats with updates applying decay since last seen."""
    merged: dict[PrefixKey, PrefixStats] = {}
    now = int(time.time() * 1000)

    def to_key(stat: PrefixStats) -> PrefixKey:
        return (stat.prefix_id, stat.tenant, stat.model_id)

    for stat in baseline:
        key = to_key(stat)
        # Decay legacy score to keep it bounded if stale.
        weight = _decay_weight(now, stat.last_seen_ms, half_life_ms)
        merged[key] = PrefixStats(
            prefix_id=stat.prefix_id,
            tenant=stat.tenant,
            model_id=stat.model_id,
            hit_count=stat.hit_count,
            total_bytes=stat.total_bytes,
            avg_latency_ms=stat.avg_latency_ms,
            score=stat.score * weight,
            last_seen_ms=stat.last_seen_ms,
        )

    for stat in updates:
        key = to_key(stat)
        existing = merged.get(key)
        if existing is None:
            merged[key] = stat
            continue
        total_hits = existing.hit_count + stat.hit_count
        combined_latency = (
            existing.avg_latency_ms * existing.hit_count + stat.avg_latency_ms * stat.hit_count
        )
        avg_latency = combined_latency / total_hits if total_hits > 0 else 0.0
        merged[key] = PrefixStats(
            prefix_id=stat.prefix_id,
            tenant=stat.tenant,
            model_id=stat.model_id,
            hit_count=total_hits,
            total_bytes=existing.total_bytes + stat.total_bytes,
            avg_latency_ms=avg_latency,
            score=existing.score + stat.score,
            last_seen_ms=max(existing.last_seen_ms, stat.last_seen_ms),
        )
    return merged
