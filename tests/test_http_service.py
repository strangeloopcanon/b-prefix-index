from __future__ import annotations

from fastapi.testclient import TestClient

from prefix_indexer.analytics import aggregate_events
from prefix_indexer.models import PrefixEvent, PrefixIndexConfig
from prefix_indexer.service_http import create_app


def _load_sample_events() -> list[PrefixEvent]:
    data = [
        {
            "prefix_id": "sess-A",
            "tenant": "tenant-a",
            "model_id": "model-x",
            "layer": 3,
            "page_start": 0,
            "page_end": 1,
            "bytes": 1024,
            "latency_ms": 5.0,
            "timestamp_ms": 1000,
        },
        {
            "prefix_id": "sess-A",
            "tenant": "tenant-a",
            "model_id": "model-x",
            "layer": 3,
            "page_start": 2,
            "page_end": 3,
            "bytes": 2048,
            "latency_ms": 7.0,
            "timestamp_ms": 2000,
        },
        {
            "prefix_id": "sess-B",
            "tenant": "tenant-b",
            "model_id": "model-y",
            "layer": 1,
            "page_start": 0,
            "page_end": 0,
            "bytes": 512,
            "latency_ms": 3.3,
            "timestamp_ms": 1500,
        },
    ]
    return [PrefixEvent.model_validate(item) for item in data]


def test_health_and_ingest_endpoint() -> None:
    app = create_app(PrefixIndexConfig(decay_half_life_ms=10_000_000))
    client = TestClient(app)

    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    payload = {"events": [event.model_dump() for event in _load_sample_events()]}
    ingest_resp = client.post("/ingest", json=payload)
    assert ingest_resp.status_code == 202
    assert ingest_resp.json() == {"ingested": len(payload["events"])}

    suggest_resp = client.get("/suggest", params={"top_k": 2})
    assert suggest_resp.status_code == 200
    body = suggest_resp.json()
    assert len(body) == 2
    assert body[0]["prefix_id"] == "sess-A"
    assert body[0]["tenant"] == "tenant-a"


def test_recommendations_match_analytics_direct_computation() -> None:
    config = PrefixIndexConfig(decay_half_life_ms=10_000_000)
    app = create_app(config)
    client = TestClient(app)

    events = _load_sample_events()
    client.post(
        "/ingest",
        json={"events": [event.model_dump() for event in events]},
    )
    suggestions = client.get("/suggest", params={"top_k": 10}).json()
    suggested_ids = {(rec["tenant"], rec["prefix_id"]) for rec in suggestions}

    aggregate = aggregate_events(events, now_ms=2_500, half_life_ms=config.decay_half_life_ms)
    expected_ids = {(stat.tenant, stat.prefix_id) for stat in aggregate.values()}
    assert suggested_ids == expected_ids
