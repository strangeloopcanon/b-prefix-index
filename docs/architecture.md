# Offline Prefix Index Architecture

## Scope

Provide a background job that mines historical KV cache traces and produces
prefix warm-up recommendations for planners such as BCache. The service must:

1. Ingest trace batches without blocking online pipelines.
2. Aggregate popularity metrics with configurable time decay.
3. Persist compact summaries for cheap lookups.
4. Expose an interface (`prefix_indexer.api`) that planners can consume on demand.

## Core Components

| Module | Responsibility |
| --- | --- |
| `prefix_indexer.models` | Typed dataclasses with light validation for trace events, aggregated stats, and recommendations. |
| `prefix_indexer.analytics` | Aggregation logic (decay-weighted scores, freshness tracking). |
| `prefix_indexer.storage` | Backend interfaces (in-memory and JSON Lines persistence for MVP). |
| `prefix_indexer.service` | Orchestrates ingestion, scoring, and persistence. |
| `prefix_indexer.api` | Public facade returning recommendations for clients. |
| `prefix_indexer.service_http` | FastAPI service exposing ingest/suggest endpoints for remote planners. |
| `prefix_indexer.cli` | CLI entrypoint for batch ingestion and diagnostics. |

## Data Model

```text
PrefixEvent
  prefix_id: str
  tenant: str
  model_id: str
  layer: int
  page_start: int
  page_end: int
  bytes: int
  latency_ms: float
  timestamp_ms: int

PrefixStats
  prefix_id: str
  tenant: str
  hit_count: int
  total_bytes: int
  avg_latency_ms: float
  score: float    # decay-weighted utility
  last_seen_ms: int

PrefixRecommendation
  prefix_id: str
  tenant: str
  score: float
  hint: str
```

## Analytics Strategy

- Use exponential time decay based on configurable half-life to emphasize recent usage.
- Clamp layer/page metadata into deterministic keys so different requests that share the
  same prefix contribute to the same aggregate.
- Provide utilities to merge aggregates from multiple batches to support incremental runs.
- Export metrics that planners can stash in their telemetry for feedback loops.

## Pluggability

- Storage backend is selected via factory (`JsonlPrefixIndexStore` by default).
- Analytics layer exposes a protocol so that Bodo or Pandas implementations can be swapped in
  later without touching callers.
- CLI supports reading JSONL today; Parquet and streaming readers can be added later.

## Interop with Planners

The planner should:

1. Periodically fetch top prefix recommendations.
2. Compare against its active cache to avoid duplicate work.
3. Report which prefetches were actually used so the offline job can adjust.

Future work will add a telemetry sink to capture planner feedback.
