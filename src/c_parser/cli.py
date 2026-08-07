from __future__ import annotations

import argparse
import sys
from pathlib import Path

from c_parser.extractors import TreeSitterExtractor
from c_parser.sink import JsonlSink, Neo4jSink, Sink


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract undocumented C/C++ entities for LLM documentation generation.",
    )
    parser.add_argument("path", type=Path, help="Source file or directory to parse")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write JSONL to this file (implies --sink jsonl)",
    )
    parser.add_argument(
        "--sink",
        choices=("neo4j", "jsonl"),
        default="neo4j",
        help="Output sink (default: neo4j). Use jsonl for stdout when -o is omitted.",
    )
    parser.add_argument(
        "--include-documented",
        action="store_true",
        help="Include entities that already have documentation comments",
    )
    parser.add_argument(
        "--strict-doc-comments",
        action="store_true",
        help="Only treat /** and /// as documentation (ignore //!)",
    )
    return parser


def _make_sink(args: argparse.Namespace) -> tuple[Sink, bool]:
    sink_kind = "jsonl" if args.output else args.sink
    if sink_kind == "jsonl":
        if args.output:
            return JsonlSink.from_path(args.output), True
        return JsonlSink(sys.stdout), False

    from config import Neo4jConfigMapper

    return Neo4jSink.from_config(Neo4jConfigMapper()), True


def _print_sink_error(exc: BaseException) -> None:
    print(f"error: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root: Path = args.path

    if not root.exists():
        print(f"error: path does not exist: {root}", file=sys.stderr)
        return 1

    extractor = TreeSitterExtractor()

    try:
        sink, close_sink = _make_sink(args)
    except (RuntimeError, FileNotFoundError, OSError, ValueError) as exc:
        _print_sink_error(exc)
        return 1

    try:
        try:
            extractor.extract(
                root,
                sink.write,
                strict_doc_comments=args.strict_doc_comments,
                include_documented=args.include_documented,
            )
        finally:
            if close_sink:
                sink.close()
    except Exception as exc:
        name = type(exc).__module__ + "." + type(exc).__name__
        if name.startswith("neo4j.") or "ServiceUnavailable" in type(exc).__name__:
            print(f"error: Neo4j connection failed: {exc}", file=sys.stderr)
            return 1
        if isinstance(exc, (OSError, RuntimeError, ConnectionError, TimeoutError)):
            _print_sink_error(exc)
            return 1
        raise

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
