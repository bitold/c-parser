from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

Direction = Literal["out", "in"]


@dataclass(frozen=True)
class NodeRelationship:
    """Relationship to upsert together with a source node."""

    type: str
    target_label: str
    target_key: str
    target_key_value: Any
    properties: Mapping[str, Any] = field(default_factory=dict)
    direction: Direction = "out"  # "out" = (n)-[r]->(t), "in" = (n)<-[r]-(t)


@dataclass(frozen=True)
class NodeUpsert:
    """Node identity + properties for single or batch upsert."""

    label: str
    key: str
    key_value: Any
    properties: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelationshipUpsert:
    """Directed relationship between two node identities: (source)-[type]->(target)."""

    type: str
    source_label: str
    source_key: str
    source_key_value: Any
    target_label: str
    target_key: str
    target_key_value: Any
    properties: Mapping[str, Any] = field(default_factory=dict)
