"""Public API facade for the offline prefix indexer."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .models import PrefixEvent, PrefixIndexConfig, PrefixRecommendation, PrefixStats
from .service import PrefixIndexService


class PrefixIndexAPI:
    """High-level façade consumed by planners or orchestration code."""

    def __init__(self, config: PrefixIndexConfig) -> None:
        self._service = PrefixIndexService(config)

    def ingest_events(self, events: Iterable[PrefixEvent]) -> None:
        """Ingest in-memory events."""
        self._service.ingest_events(list(events))

    def ingest_file(self, path: str | Path) -> None:
        """Load a JSONL file and ingest."""
        self._service.ingest_jsonl(Path(path))

    def recommendations(
        self,
        *,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> list[PrefixRecommendation]:
        """Return ranked prefix recommendations."""
        return self._service.recommendations(top_k=top_k, min_score=min_score)

    def snapshot(self) -> list[PrefixStats]:
        """Return the raw statistics."""
        return self._service.export_snapshot()

    def snapshot_json(self) -> str:
        """Serialize the full index as JSON."""
        return self._service.dump_json()


def build_api(config: PrefixIndexConfig | None = None) -> PrefixIndexAPI:
    """Convenience constructor with defaults."""
    return PrefixIndexAPI(config or PrefixIndexConfig())
