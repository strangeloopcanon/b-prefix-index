"""CLI entrypoint for the offline prefix indexer."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .api import PrefixIndexAPI
from .models import PrefixIndexConfig


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prefix-indexer", description="Offline prefix index utility."
    )
    parser.add_argument("--store", type=Path, help="Path to persistent JSONL store.")
    parser.add_argument(
        "--half-life-ms",
        type=int,
        default=3_600_000,
        help="Half-life window for score decay (milliseconds).",
    )
    parser.add_argument(
        "--max-recs",
        type=int,
        default=100,
        help="Maximum recommendations to return by default.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Minimum score filter used for recommendations.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Ingest a JSONL trace file.")
    ingest.add_argument("path", type=Path, help="Path to trace JSONL.")

    suggest = sub.add_parser("suggest", help="Print recommendations.")
    suggest.add_argument("--top-k", type=int, default=10, help="Number of recommendations to show.")
    suggest.add_argument(
        "--min-score", type=float, default=None, help="Optional per-call score floor."
    )

    dump = sub.add_parser("dump", help="Dump raw stats as JSON.")
    dump.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")

    return parser


def _config_from_args(args: argparse.Namespace) -> PrefixIndexConfig:
    return PrefixIndexConfig(
        decay_half_life_ms=args.half_life_ms,
        max_recommendations=args.max_recs,
        min_score=args.min_score,
        store_path=str(args.store) if args.store else None,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = _config_from_args(args)
    api = PrefixIndexAPI(config)

    if args.command == "ingest":
        api.ingest_file(args.path)
        return 0
    if args.command == "suggest":
        recs = api.recommendations(top_k=args.top_k, min_score=args.min_score)
        if not recs:
            print("No recommendations above threshold.", file=sys.stdout)
            return 0
        for rec in recs:
            print(
                f"{rec.tenant}/{rec.model_id}/{rec.prefix_id} -> score={rec.score:.2f} ({rec.hint})"
            )
        return 0
    if args.command == "dump":
        data = api.snapshot_json()
        if args.pretty:
            print(data)
        else:
            print(data.replace("\n", ""), file=sys.stdout)
        return 0
    parser.error(f"Unsupported command {args.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
