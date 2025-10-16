from __future__ import annotations

from pathlib import Path

from prefix_indexer.api import PrefixIndexAPI
from prefix_indexer.models import PrefixEvent, PrefixIndexConfig


def test_service_ingest_and_recommendations(tmp_path: Path) -> None:
    store = tmp_path / "index.jsonl"
    api = PrefixIndexAPI(
        PrefixIndexConfig(
            decay_half_life_ms=10_000_000, store_path=str(store), max_recommendations=5
        )
    )
    events = [
        PrefixEvent(
            prefix_id="pfx-A",
            tenant="tenant-a",
            model_id="model-x",
            layer=3,
            page_start=0,
            page_end=1,
            bytes=1024,
            latency_ms=5.0,
            timestamp_ms=1000,
        ),
        PrefixEvent(
            prefix_id="pfx-B",
            tenant="tenant-a",
            model_id="model-x",
            layer=3,
            page_start=2,
            page_end=3,
            bytes=2048,
            latency_ms=7.0,
            timestamp_ms=2000,
        ),
    ]

    api.ingest_events(events)
    recs = api.recommendations(top_k=2)
    assert len(recs) == 2
    assert recs[0].prefix_id == "pfx-B"
    assert "hits=1" in recs[0].hint

    # Ensure persistence round-trip
    api2 = PrefixIndexAPI(
        PrefixIndexConfig(
            decay_half_life_ms=10_000_000, store_path=str(store), max_recommendations=5
        )
    )
    recs2 = api2.recommendations(top_k=1)
    assert recs2[0].prefix_id == recs[0].prefix_id
