from __future__ import annotations

from dataclasses import dataclass, field

from tree_sitter import Node

from c_parser.extractors.treesitter.utils import node_text
from c_parser.extractors.treesitter.mappers import make_entity
from c_parser.models import Entity, EntityKind, Language

NodeKey = tuple[str, int, int]


@dataclass
class _Ctx:
    source: bytes
    path: str
    language: Language
    strict_doc_comments: bool
    entities: list[Entity] = field(default_factory=list)
    entity_ids_by_node: dict[NodeKey, list[str]] = field(default_factory=dict)


def _emit(
    ctx: _Ctx,
    kind: EntityKind,
    name: str,
    node: Node,
    *,
    signature: str | None = None,
) -> Entity:
    entity = make_entity(
        kind=kind,
        name=name,
        language=ctx.language,
        path=ctx.path,
        node=node,
        source=ctx.source,
        signature=signature if signature is not None else node_text(ctx.source, node).strip(),
        strict_doc_comments=ctx.strict_doc_comments,
    )
    ctx.entities.append(entity)
    ctx.entity_ids_by_node.setdefault(node_key(node), []).append(entity.id)
    return entity


def node_key(node: Node) -> NodeKey:
    return (node.type, node.start_byte, node.end_byte)


def entity_ids_for_node(ctx: _Ctx, node: Node) -> list[str]:
    return ctx.entity_ids_by_node.get(node_key(node), [])


def _is_function_declaration(node: Node) -> bool:
    decl = node.child_by_field_name("declarator")
    return decl is not None and _has_function_declarator(decl)


def _has_function_declarator(node: Node) -> bool:
    if node.type == "function_declarator":
        return True
    return any(c.is_named and _has_function_declarator(c) for c in node.children)

