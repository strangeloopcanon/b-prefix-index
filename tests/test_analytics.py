from __future__ import annotations

import time

import pytest

from prefix_indexer.analytics import aggregate_events, merge_stats
from prefix_indexer.models import PrefixEvent, PrefixStats


def _event(prefix: str, timestamp_ms: int, bytes_: int = 1000) -> PrefixEvent:
    return PrefixEvent(
        prefix_id=prefix,
        tenant="tenant",
        model_id="model",
        layer=0,
        page_start=0,
        page_end=0,
        bytes=bytes_,
        latency_ms=5.0,
        timestamp_ms=timestamp_ms,
    )


def test_aggregate_events_groups_by_prefix() -> None:
    now = int(time.time() * 1000)
    events = [
        _event("pfx-A", now - 1_000, bytes_=512),
        _event("pfx-A", now - 500, bytes_=512),
        _event("pfx-B", now - 100, bytes_=256),
    ]
    result = aggregate_events(events, now_ms=now, half_life_ms=10_000_000)
    assert len(result) == 2
    a_stats = result[("pfx-A", "tenant", "model")]
    assert a_stats.hit_count == 2
    assert a_stats.total_bytes == 1024
    assert a_stats.last_seen_ms == events[1].timestamp_ms
    assert a_stats.score == pytest.approx(1024, rel=1e-3)


def test_merge_stats_combines_existing() -> None:
    now = int(time.time() * 1000)
    base = [
        PrefixStats(
            prefix_id="pfx-A",
            tenant="tenant",
            model_id="model",
            hit_count=3,
            total_bytes=1500,
            avg_latency_ms=6.0,
            score=1200.0,
            last_seen_ms=now - 60_000,
        )
    ]
    updates = [
        PrefixStats(
            prefix_id="pfx-A",
            tenant="tenant",
            model_id="model",
            hit_count=2,
            total_bytes=800,
            avg_latency_ms=4.0,
            score=700.0,
            last_seen_ms=now,
        )
    ]
    merged = merge_stats(base, updates, half_life_ms=3600_000)
    stat = merged[("pfx-A", "tenant", "model")]
    assert stat.hit_count == 5
    assert stat.total_bytes == 2300
    assert stat.avg_latency_ms < 6.0  # blended downward by faster updates
    assert stat.last_seen_ms == now
