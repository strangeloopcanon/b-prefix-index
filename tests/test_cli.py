from __future__ import annotations

import json
from pathlib import Path

from prefix_indexer import cli


def test_cli_ingest_and_dump(tmp_path: Path) -> None:
    store = tmp_path / "store.jsonl"
    events = tmp_path / "events.jsonl"
    events.write_text(
        '{"prefix_id": "pfx-1", "tenant": "tenant", "model_id": "model", "layer": 0, '
        '"page_start": 0, "page_end": 0, "bytes": 128, "latency_ms": 5.0, "timestamp_ms": 10}\n'
    )

    assert (
        cli.main(
            [
                "--store",
                str(store),
                "ingest",
                str(events),
            ]
        )
        == 0
    )

    dump_output = cli.main(["--store", str(store), "dump", "--pretty"])
    assert dump_output == 0
    data = json.loads(store.read_text().splitlines()[0])
    assert data["prefix_id"] == "pfx-1"
