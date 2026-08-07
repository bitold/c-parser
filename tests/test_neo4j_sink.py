from __future__ import annotations

from unittest.mock import MagicMock

from neo4j_api.models import NodeUpsert, RelationshipUpsert

from c_parser.models import Entity, EntityKind, Language, Relation, Relationship
from c_parser.sink.neo4j import Neo4jSink


def test_neo4j_sink_flush_uses_atomic_upsert_graph():
    client = MagicMock()
    sink = Neo4jSink(client)
    entity = Entity(
        id="f::function::add::1",
        kind=EntityKind.FUNCTION,
        name="add",
        language=Language.C,
        path="f.c",
        start_line=1,
        end_line=3,
        signature="int add(int a, int b)",
        body="int add(int a, int b) { return a + b; }",
        has_documentation=False,
        relationships=[
            Relation(type=Relationship.CALLS, target_id="f::function::other::5"),
        ],
    )
    sink.write(entity)
    sink.flush()

    client.upsert_graph.assert_called_once()
    nodes, relationships = client.upsert_graph.call_args.args
    assert len(nodes) == 1
    assert isinstance(nodes[0], NodeUpsert)
    assert nodes[0].key_value == entity.id
    assert len(relationships) == 1
    assert isinstance(relationships[0], RelationshipUpsert)
    assert relationships[0].type == "CALLS"
    client.upsert_nodes.assert_not_called()
    client.upsert_relationships.assert_not_called()
