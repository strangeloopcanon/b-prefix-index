# Offline Prefix Index

Offline sidecar that precomputes popularity signals for KV-cache planners such as BCache.  
It ingests historical request traces, aggregates prefix statistics, and emits warm-up
recommendations that online planners can opt-in to consume without blocking their tight
planning windows.

## Goals

- Maintain a pluggable index that any planner can query for popular `prefix_id` entries.
- Keep runtime interaction decoupled: the live planner can pull hints when appropriate, but
  the offline job never sits on the critical 20 ms decision loop.
- Provide a clear API surface (`prefix_indexer.api`) with statically typed Pydantic models.
- Leave room for Bodo-powered accelerators when data volumes require it.

## High-Level Flow

1. **Ingest traces** – Accept JSONL/Parquet slices of KV cache requests.
2. **Aggregate** – Use exponential-decay popularity scoring and freshness tracking.
3. **Persist** – Store compact summaries in a JSONL (default) or pluggable backend.
4. **Recommend** – Expose top-k prefix candidates for background warm-ups.

```
┌───────────────────┐    batched traces   ┌─────────────────────┐
│ Trace collectors   │ ─────────────────▶ │ Ingest/analytics     │
└───────────────────┘                     │ (PrefixIndexService) │
                                          └─────────┬───────────┘
                                                    │
                                          persisted index snapshots
                                                    │
                                          ┌─────────▼───────────┐
                                          │ Prefix index store   │
                                          └─────────┬───────────┘
                                                    │
                                          background hint queries
                                                    │
                                          ┌─────────▼───────────┐
                                          │ Online planners      │
                                          └─────────────────────┘
```

## Repository Layout

```
prefix_indexer/        Core library (API, models, analytics, storage, CLI)
tests/                 Pytest-based unit tests
docs/                  Design notes and future work
scripts/               Utility entrypoints (reserved)
examples/              Sample trace data
results/               Evaluation output (gitignored)
```

## Quick Start

```bash
make setup
prefix-indexer ingest examples/sample_events.jsonl
prefix-indexer suggest --top-k 5

# Run HTTP service (optional)
prefix-indexer-http --host 127.0.0.1 --port 8080
# In another shell
curl -X POST http://127.0.0.1:8080/ingest \
  -H "content-type: application/json" \
  -d @<(python - <<'PY'
import json
from pathlib import Path
events = [json.loads(line) for line in Path('examples/sample_events.jsonl').read_text().splitlines()]
print(json.dumps({"events": events}))
PY)
curl 'http://127.0.0.1:8080/suggest?top_k=5'
```

## Interface Contract

Use the `Makefile` targets: `setup`, `check`, `test`, `llm-live`, `deps-audit`, `all`, `release`.  
See `Makefile` for concrete commands. Tools such as Black/Ruff/Mypy run only when available so the project can operate in offline environments.

## Future Enhancements

- Optional Bodo accelerator for the analytics layer.
- Parquet-backed ingestion and delta updates.
- gRPC/HTTP service for remote planners.
- Cost-aware hint throttling and planner feedback loops.
