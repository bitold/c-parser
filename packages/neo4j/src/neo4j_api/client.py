from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from neo4j import GraphDatabase, RoutingControl

from neo4j_api.cypher_identifiers import require_cypher_identifier
from neo4j_api.models import NodeRelationship, NodeUpsert, RelationshipUpsert
from neo4j_api.protocols import Neo4jConfig
from neo4j_api.record_serializer import serialize_records


class Neo4jClient:
    """Thin Neo4j API: node/rel CRUD helpers, query, and arbitrary Cypher."""

    def __init__(self, config: Neo4jConfig) -> None:
        self._config = config
        self._driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password),
        )

    @property
    def config(self) -> Neo4jConfig:
        return self._config

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> Neo4jClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def verify_connectivity(self) -> None:
        self._driver.verify_connectivity()

    ping = verify_connectivity

    def get_node(
        self,
        *,
        label: str,
        key: str,
        key_value: Any,
    ) -> dict[str, Any] | None:
        """Return one node matched by `(label, key=key_value)`, or ``None``."""
        label = require_cypher_identifier(label, kind="label")
        key = require_cypher_identifier(key, kind="property")
        rows = self.query(
            f"MATCH (n:{label} {{{key}: $key_value}}) RETURN n LIMIT 1",
            {"key_value": key_value},
        )
        if not rows:
            return None
        return rows[0].get("n")

    def delete_node(
        self,
        *,
        label: str,
        key: str,
        key_value: Any,
        detach: bool = True,
    ) -> None:
        """Delete a node matched by `(label, key=key_value)`.

        With ``detach=True`` (default) also deletes its relationships.
        """
        label = require_cypher_identifier(label, kind="label")
        key = require_cypher_identifier(key, kind="property")
        delete = "DETACH DELETE n" if detach else "DELETE n"
        self.execute(
            f"MATCH (n:{label} {{{key}: $key_value}}) {delete}",
            {"key_value": key_value},
        )

    def upsert_node(
        self,
        *,
        label: str,
        key: str,
        key_value: Any,
        properties: Mapping[str, Any] | None = None,
        relationships: Sequence[NodeRelationship] | None = None,
    ) -> None:
        """MERGE a node by `(label, key=key_value)`, set properties, upsert relationships."""
        label = require_cypher_identifier(label, kind="label")
        key = require_cypher_identifier(key, kind="property")
        props = dict(properties or {})
        props.pop(key, None)

        cypher = (
            f"MERGE (n:{label} {{{key}: $key_value}})\n"
            "SET n += $props\n"
        )
        params: dict[str, Any] = {"key_value": key_value, "props": props}

        for index, rel in enumerate(relationships or ()):
            rel_type = require_cypher_identifier(rel.type, kind="relationship type")
            target_label = require_cypher_identifier(rel.target_label, kind="label")
            target_key = require_cypher_identifier(rel.target_key, kind="property")
            if rel.direction not in ("out", "in"):
                raise ValueError(f"Invalid relationship direction: {rel.direction!r}")

            t_alias = f"t{index}"
            r_alias = f"r{index}"
            kv_param = f"target_key_value_{index}"
            rp_param = f"rel_props_{index}"

            if rel.direction == "out":
                pattern = f"(n)-[{r_alias}:{rel_type}]->({t_alias})"
            else:
                pattern = f"(n)<-[{r_alias}:{rel_type}]-({t_alias})"

            cypher += (
                f"MERGE ({t_alias}:{target_label} {{{target_key}: ${kv_param}}})\n"
                f"MERGE {pattern}\n"
                f"SET {r_alias} += ${rp_param}\n"
            )
            params[kv_param] = rel.target_key_value
            params[rp_param] = dict(rel.properties)

        self.execute(cypher, params)

    def upsert_relationship(self, rel: RelationshipUpsert) -> None:
        """MERGE a directed relationship `(source)-[type]->(target)` and set properties."""
        self.upsert_relationships([rel])

    def upsert_nodes(self, nodes: Sequence[NodeUpsert]) -> None:
        """Batch-MERGE nodes via ``UNWIND``, grouped by ``(label, key)``."""
        for cypher, params in _node_upsert_ops(nodes):
            self.execute(cypher, params)

    def upsert_relationships(self, relationships: Sequence[RelationshipUpsert]) -> None:
        """Batch-MERGE relationships via ``UNWIND``, grouped by endpoint labels/keys/type."""
        for cypher, params in _relationship_upsert_ops(relationships):
            self.execute(cypher, params)

    def upsert_graph(
        self,
        nodes: Sequence[NodeUpsert],
        relationships: Sequence[RelationshipUpsert],
    ) -> None:
        """Atomically upsert nodes then relationships in one write transaction.

        Avoids a partial graph when relationship upsert fails after nodes landed.
        """
        ops = list(_node_upsert_ops(nodes)) + list(_relationship_upsert_ops(relationships))
        if not ops:
            return

        def _work(tx: Any) -> None:
            for cypher, params in ops:
                tx.run(cypher, params)

        with self._driver.session(database=self._config.database) as session:
            session.execute_write(_work)

    def query(
        self,
        cypher: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run a read Cypher query (routed to readers when available)."""
        records, _, _ = self._driver.execute_query(
            cypher,
            parameters_=dict(parameters or {}),
            routing_=RoutingControl.READ,
            database_=self._config.database,
        )
        return serialize_records(records)

    def execute(
        self,
        cypher: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run an arbitrary Cypher statement (read or write)."""
        records, _, _ = self._driver.execute_query(
            cypher,
            parameters_=dict(parameters or {}),
            database_=self._config.database,
        )
        return serialize_records(records)


def _node_upsert_ops(
    nodes: Sequence[NodeUpsert],
) -> list[tuple[str, dict[str, Any]]]:
    if not nodes:
        return []

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        label = require_cypher_identifier(node.label, kind="label")
        key = require_cypher_identifier(node.key, kind="property")
        props = dict(node.properties)
        props.pop(key, None)
        groups[(label, key)].append({"key_value": node.key_value, "props": props})

    return [
        (
            (
                "UNWIND $rows AS row\n"
                f"MERGE (n:{label} {{{key}: row.key_value}})\n"
                "SET n += row.props"
            ),
            {"rows": rows},
        )
        for (label, key), rows in groups.items()
    ]


def _relationship_upsert_ops(
    relationships: Sequence[RelationshipUpsert],
) -> list[tuple[str, dict[str, Any]]]:
    if not relationships:
        return []

    groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for rel in relationships:
        rel_type = require_cypher_identifier(rel.type, kind="relationship type")
        source_label = require_cypher_identifier(rel.source_label, kind="label")
        source_key = require_cypher_identifier(rel.source_key, kind="property")
        target_label = require_cypher_identifier(rel.target_label, kind="label")
        target_key = require_cypher_identifier(rel.target_key, kind="property")
        groups[(rel_type, source_label, source_key, target_label, target_key)].append(
            {
                "source_key_value": rel.source_key_value,
                "target_key_value": rel.target_key_value,
                "props": dict(rel.properties),
            }
        )

    return [
        (
            (
                "UNWIND $rows AS row\n"
                f"MERGE (a:{source_label} {{{source_key}: row.source_key_value}})\n"
                f"MERGE (b:{target_label} {{{target_key}: row.target_key_value}})\n"
                f"MERGE (a)-[r:{rel_type}]->(b)\n"
                "SET r += row.props"
            ),
            {"rows": rows},
        )
        for (rel_type, source_label, source_key, target_label, target_key), rows in groups.items()
    ]
