from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EntityKind(str, Enum):
    FILE = "file"
    FUNCTION = "function"
    STRUCT = "struct"
    UNION = "union"
    CLASS = "class"
    ENUM = "enum"
    ENUMERATOR = "enumerator"
    TYPEDEF = "typedef"
    VARIABLE = "variable"
    FIELD = "field"
    MACRO = "macro"
    NAMESPACE = "namespace"


class Language(str, Enum):
    C = "c"
    CPP = "cpp"


class Relationship(str, Enum):
    """Edge type from this entity to another (target_id)."""

    MEMBER = "member"  # this entity is a member of target
    INHERITS = "inherits"
    DEFINES = "defines"
    CALLS = "calls"
    INCLUDES = "includes"  # file → included file
    DECLARES = "declares"  # file → function declaration
    IMPLEMENTS = "implements"  # implementation → declaration / header


@dataclass(frozen=True)
class Relation:
    type: Relationship
    target_id: str

    def to_dict(self) -> dict[str, str]:
        return {"type": self.type.value, "target_id": self.target_id}


@dataclass(frozen=True)
class Entity:
    """Parsed source entity for LLM documentation generation."""

    id: str
    kind: EntityKind
    name: str
    language: Language
    path: str
    start_line: int
    end_line: int
    signature: str
    body: str
    has_documentation: bool
    relationships: list[Relation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "name": self.name,
            "language": self.language.value,
            "path": self.path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "signature": self.signature,
            "body": self.body,
            "has_documentation": self.has_documentation,
            "relationships": [rel.to_dict() for rel in self.relationships],
        }
