"""Storage backends for prefix statistics."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .models import PrefixIndexConfig, PrefixStats


class PrefixIndexStore(Protocol):
    """Abstract store contract."""

    def load(self) -> None: ...

    def list_stats(self) -> list[PrefixStats]: ...

    def bulk_upsert(self, stats: Iterable[PrefixStats]) -> None: ...

    def clear(self) -> None: ...


@dataclass
class InMemoryPrefixIndexStore(PrefixIndexStore):
    """Simple in-memory store, convenient for tests."""

    _stats: dict[tuple[str, str, str], PrefixStats] = field(default_factory=dict)

    def load(self) -> None:
        return None

    def list_stats(self) -> list[PrefixStats]:
        return list(self._stats.values())

    def bulk_upsert(self, stats: Iterable[PrefixStats]) -> None:
        for stat in stats:
            key = (stat.prefix_id, stat.tenant, stat.model_id)
            self._stats[key] = stat

    def clear(self) -> None:
        self._stats.clear()


@dataclass
class JsonlPrefixIndexStore(PrefixIndexStore):
    """Persist statistics to a JSONL file."""

    path: Path
    _stats: InMemoryPrefixIndexStore = field(default_factory=InMemoryPrefixIndexStore)

    def load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()
        parsed: list[PrefixStats] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            parsed.append(PrefixStats.model_validate(data))
        self._stats.clear()
        self._stats.bulk_upsert(parsed)

    def list_stats(self) -> list[PrefixStats]:
        return self._stats.list_stats()

    def bulk_upsert(self, stats: Iterable[PrefixStats]) -> None:
        self._stats.bulk_upsert(stats)
        self._flush()

    def clear(self) -> None:
        self._stats.clear()
        if self.path.exists():
            self.path.unlink()

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            for stat in self._stats.list_stats():
                fh.write(stat.model_dump_json())
                fh.write("\n")


def create_store(config: PrefixIndexConfig) -> PrefixIndexStore:
    """Factory helper selecting the appropriate store."""
    if config.store_path:
        return JsonlPrefixIndexStore(path=Path(config.store_path))
    return InMemoryPrefixIndexStore()
