from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from neo4j import Record
from neo4j.graph import Node, Path, Relationship


def serialize_neo4j_value(value: Any) -> Any:
    """Convert a neo4j driver value (Node/Relationship/Path/…) into plain Python dict.
    Accepts Nodes, Relationships, Paths and lists and dicts of those."""
    if isinstance(value, Node):
        return {
            "id": value.element_id,
            "labels": list(value.labels),
            "properties": dict(value),
        }
    if isinstance(value, Relationship):
        return {
            "id": value.element_id,
            "type": value.type,
            "start": value.start_node.element_id if value.start_node else None,
            "end": value.end_node.element_id if value.end_node else None,
            "properties": dict(value),
        }
    if isinstance(value, Path):
        return {
            "nodes": [serialize_neo4j_value(n) for n in value.nodes],
            "relationships": [serialize_neo4j_value(r) for r in value.relationships],
        }
    if isinstance(value, list):
        return [serialize_neo4j_value(v) for v in value]
    if isinstance(value, dict):
        return {k: serialize_neo4j_value(v) for k, v in value.items()}
    return value


def serialize_records(records: Sequence[Record]) -> list[dict[str, Any]]:
    """Convert a sequence of Neo4j records into a list of plain dicts."""
    return [
        {key: serialize_neo4j_value(record[key]) for key in record.keys()}
        for record in records
    ]
