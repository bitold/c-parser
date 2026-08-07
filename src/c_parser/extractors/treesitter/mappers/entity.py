from __future__ import annotations

from pathlib import Path

from tree_sitter import Node

from c_parser.extractors.treesitter.doc_detect import has_preceding_doc_comment
from c_parser.extractors.treesitter.mappers.relation import (
    enclosing_container_node,
    enclosing_enum_node,
)
from c_parser.extractors.treesitter.utils import end_line_number, line_number, node_text
from c_parser.models import Entity, EntityKind, Language, Relation
from c_parser.utils import entity_id


def make_file_entity(*, path: str, language: Language, source: str) -> Entity:
    """Synthetic entity for a translation unit / header file."""
    name = Path(path).name
    if source:
        end_line = source.count("\n") + (0 if source.endswith("\n") else 1)
    else:
        end_line = 1
    return Entity(
        id=entity_id(path, EntityKind.FILE.value, name, 1),
        kind=EntityKind.FILE,
        name=name,
        language=language,
        path=path,
        start_line=1,
        end_line=max(1, end_line),
        signature=path,
        body="",
        has_documentation=False,
    )


def make_entity(
    *,
    kind: EntityKind,
    name: str,
    language: Language,
    path: str,
    node: Node,
    source: bytes,
    signature: str,
    strict_doc_comments: bool,
    relationships: list[Relation] | None = None,
) -> Entity:
    has_docs = has_preceding_doc_comment(node, source, strict=strict_doc_comments)
    if not has_docs and kind in {EntityKind.FIELD, EntityKind.ENUMERATOR}:
        container = enclosing_container_node(node) or enclosing_enum_node(node)
        if container is not None:
            has_docs = has_preceding_doc_comment(
                container, source, strict=strict_doc_comments
            )
    start_line = line_number(node)
    return Entity(
        id=entity_id(path, kind.value, name, start_line),
        kind=kind,
        name=name,
        language=language,
        path=path,
        start_line=start_line,
        end_line=end_line_number(node),
        signature=signature.strip(),
        body=node_text(source, node).strip(),
        has_documentation=has_docs,
        relationships=list(relationships or ()),
    )
