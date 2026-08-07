from __future__ import annotations

from dataclasses import dataclass, field

from c_parser.models import Relationship


@dataclass(frozen=True)
class DirectRelationFact:
    type: Relationship
    source_id: str
    target_id: str


@dataclass(frozen=True)
class NamedRelationFact:
    type: Relationship
    source_id: str
    target_name: str


@dataclass(frozen=True)
class IncludeFact:
    source_path: str
    included_path: str
    angled: bool  # True for <...>, False for "..."


@dataclass
class RelationFacts:
    direct: list[DirectRelationFact] = field(default_factory=list)
    named: list[NamedRelationFact] = field(default_factory=list)
    includes: list[IncludeFact] = field(default_factory=list)
