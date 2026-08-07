from __future__ import annotations

from tree_sitter import Node

from c_parser.extractors.treesitter.core import _Ctx, entity_ids_for_node
from c_parser.extractors.treesitter.mappers.relation import (
    base_class_names,
    callee_name,
    member_of_enum_relation,
    member_of_relation,
)
from c_parser.extractors.treesitter.relations.facts import (
    DirectRelationFact,
    IncludeFact,
    NamedRelationFact,
    RelationFacts,
)
from c_parser.extractors.treesitter.utils import node_text
from c_parser.models import Relationship

_NON_MEMBER_NODE_TYPES = frozenset(
    {"preproc_def", "preproc_function_def"}
)


class RelationHandler:
    """Collect unresolved relation facts while visiting AST nodes."""

    def handle(self, node: Node, ctx: _Ctx, facts: RelationFacts) -> None:
        self._collect_member(node, ctx, facts)

        match node.type:
            case "class_specifier":
                self._collect_inherits(node, ctx, facts)
            case "call_expression":
                self._collect_call(node, ctx, facts)
            case "preproc_include":
                self._collect_include(node, ctx, facts)

    def _collect_member(
        self,
        node: Node,
        ctx: _Ctx,
        facts: RelationFacts,
    ) -> None:
        if node.type in _NON_MEMBER_NODE_TYPES:
            return

        source_ids = entity_ids_for_node(ctx, node)
        if not source_ids:
            return

        relation = (
            member_of_enum_relation(node, ctx.path)
            if node.type == "enumerator"
            else member_of_relation(node, ctx.path)
        )
        if relation is None:
            return

        facts.direct.extend(
            DirectRelationFact(
                type=relation.type,
                source_id=source_id,
                target_id=relation.target_id,
            )
            for source_id in source_ids
        )

    def _collect_inherits(
        self,
        node: Node,
        ctx: _Ctx,
        facts: RelationFacts,
    ) -> None:
        source_ids = entity_ids_for_node(ctx, node)
        if len(source_ids) != 1:
            return

        facts.named.extend(
            NamedRelationFact(
                type=Relationship.INHERITS,
                source_id=source_ids[0],
                target_name=base,
            )
            for base in base_class_names(node)
        )

    def _collect_call(
        self,
        node: Node,
        ctx: _Ctx,
        facts: RelationFacts,
    ) -> None:
        function = node.child_by_field_name("function")
        if function is None:
            return
        name = callee_name(function)
        if not name:
            return

        definition = _enclosing_function_definition(node)
        if definition is None:
            return
        source_ids = entity_ids_for_node(ctx, definition)
        if len(source_ids) != 1:
            return

        facts.named.append(
            NamedRelationFact(
                type=Relationship.CALLS,
                source_id=source_ids[0],
                target_name=name,
            )
        )

    def _collect_include(
        self,
        node: Node,
        ctx: _Ctx,
        facts: RelationFacts,
    ) -> None:
        path_node = node.child_by_field_name("path")
        if path_node is None:
            return

        raw = node_text(ctx.source, path_node).strip()
        if len(raw) < 2:
            return
        angled = raw.startswith("<") and raw.endswith(">")
        quoted = raw.startswith('"') and raw.endswith('"')
        if not angled and not quoted:
            return

        facts.includes.append(
            IncludeFact(
                source_path=ctx.path,
                included_path=raw[1:-1],
                angled=angled,
            )
        )


def _enclosing_function_definition(node: Node) -> Node | None:
    parent = node.parent
    while parent is not None:
        if parent.type == "function_definition":
            return parent
        parent = parent.parent
    return None
