from __future__ import annotations

import json
from pathlib import Path

from c_parser.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_writes_undocumented_only(tmp_path: Path):
    output = tmp_path / "out.jsonl"
    code = main([str(FIXTURES / "mixed.c"), "-o", str(output)])

    assert code == 0
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").strip().splitlines()]
    by_kind = {r["kind"]: r for r in rows}
    assert set(by_kind) == {"file", "function"}
    assert by_kind["file"]["name"] == "mixed.c"
    assert by_kind["function"]["name"] == "undocumented_sub"
    assert by_kind["function"]["has_documentation"] is False


def test_cli_include_documented(tmp_path: Path):
    output = tmp_path / "out.jsonl"
    code = main([str(FIXTURES / "mixed.c"), "-o", str(output), "--include-documented"])

    assert code == 0
    names = {json.loads(line)["name"] for line in output.read_text(encoding="utf-8").splitlines()}
    assert "mixed.c" in names
    assert "documented_add" in names
    assert "undocumented_sub" in names


def test_cli_simple_app_includes_and_declares(tmp_path: Path):
    root = Path(__file__).resolve().parents[1] / "testdata" / "simple_app"
    output = tmp_path / "out.jsonl"
    code = main([str(root), "-o", str(output)])

    assert code == 0
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    by_id = {r["id"]: r for r in rows}

    app = next(r for r in rows if r["kind"] == "file" and r["name"] == "app.c")
    include_names = {by_id[rel["target_id"]]["name"] for rel in app["relationships"] if rel["type"] == "includes"}
    assert include_names == {"math_utils.h", "string_utils.h"}

    add_decl = next(
        r for r in rows if r["name"] == "add" and r["kind"] == "function" and r["path"].endswith(".h")
    )
    add_def = next(
        r for r in rows if r["name"] == "add" and r["kind"] == "function" and r["path"].endswith(".c")
    )
    math_header = next(
        r for r in rows if r["kind"] == "file" and r["name"] == "math_utils.h"
    )
    math_source = next(
        r for r in rows if r["kind"] == "file" and r["name"] == "math_utils.c"
    )

    assert add_decl["id"] in {
        rel["target_id"]
        for rel in math_header["relationships"]
        if rel["type"] == "declares"
    }
    assert add_def["id"] in {
        rel["target_id"]
        for rel in math_source["relationships"]
        if rel["type"] == "defines"
    }
    assert add_decl["id"] in {
        rel["target_id"]
        for rel in add_def["relationships"]
        if rel["type"] == "implements"
    }
    assert math_header["id"] in {
        rel["target_id"]
        for rel in math_source["relationships"]
        if rel["type"] == "implements"
    }


def test_cli_neo4j_unavailable_message(capsys, monkeypatch):
    from neo4j.exceptions import ServiceUnavailable

    class BoomSink:
        def write(self, entity) -> None:
            return None

        def close(self) -> None:
            raise ServiceUnavailable("Neo4j unavailable for test")

    monkeypatch.setattr(
        "c_parser.cli._make_sink",
        lambda args: (BoomSink(), True),
    )
    code = main([str(FIXTURES / "undocumented.c"), "--sink", "neo4j"])
    captured = capsys.readouterr()
    assert code == 1
    assert "Neo4j connection failed" in captured.err
    assert "unavailable for test" in captured.err


def test_cli_neo4j_missing_env_message(capsys, monkeypatch):
    def boom(_args):
        raise RuntimeError("Missing required env var: NEO4J_URI")

    monkeypatch.setattr("c_parser.cli._make_sink", boom)
    code = main([str(FIXTURES / "undocumented.c"), "--sink", "neo4j"])
    captured = capsys.readouterr()
    assert code == 1
    assert "Missing required env var: NEO4J_URI" in captured.err
