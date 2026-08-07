from __future__ import annotations

from neo4j_api import Neo4jClient, NodeUpsert, RelationshipUpsert
from neo4j_api.protocols import Neo4jConfig

from c_parser.models import Entity

_ENTITY_LABEL = "Entity"
_ENTITY_KEY = "id"


class Neo4jSink:
    """Buffer entities and flush them as Neo4j nodes + relationships on close.

    Entities are held in memory until ``flush``/``close``. For very large
    corpora, call ``flush`` periodically or prefer the JSONL sink.
    """

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client
        self._entities: list[Entity] = []

    @classmethod
    def from_config(cls, config: Neo4jConfig) -> Neo4jSink:
        return cls(Neo4jClient(config))

    def write(self, entity: Entity) -> None:
        self._entities.append(entity)

    def close(self) -> None:
        try:
            self.flush()
        finally:
            self._client.close()

    def flush(self) -> None:
        if not self._entities:
            return

        nodes = [
            NodeUpsert(
                label=_ENTITY_LABEL,
                key=_ENTITY_KEY,
                key_value=entity.id,
                properties={
                    "kind": entity.kind.value,
                    "name": entity.name,
                    "language": entity.language.value,
                    "path": entity.path,
                    "start_line": entity.start_line,
                    "end_line": entity.end_line,
                    "signature": entity.signature,
                    "has_documentation": entity.has_documentation,
                },
            )
            for entity in self._entities
        ]
        relationships: list[RelationshipUpsert] = []
        for entity in self._entities:
            for rel in entity.relationships:
                relationships.append(
                    RelationshipUpsert(
                        type=rel.type.value.upper(),
                        source_label=_ENTITY_LABEL,
                        source_key=_ENTITY_KEY,
                        source_key_value=entity.id,
                        target_label=_ENTITY_LABEL,
                        target_key=_ENTITY_KEY,
                        target_key_value=rel.target_id,
                    )
                )
        # Single transaction so a relationship failure does not leave orphan nodes.
        self._client.upsert_graph(nodes, relationships)
        self._entities.clear()
