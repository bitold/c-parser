from __future__ import annotations

from tree_sitter import Node

from c_parser.extractors.treesitter.core import _Ctx, _emit
from c_parser.extractors.treesitter.mappers import (
    enumerator_name,
    field_declaration_names,
)
from c_parser.extractors.treesitter.utils import (
    declarator_name,
    function_name,
    macro_name,
    signature_for_function,
    type_name,
)
from c_parser.models import EntityKind


def handle_function_definition(node: Node, ctx: _Ctx) -> None:
    if name := function_name(node):
        _emit(
            ctx,
            EntityKind.FUNCTION,
            name,
            node,
            signature=signature_for_function(node, ctx.source),
        )


def handle_function_declaration(node: Node, ctx: _Ctx) -> None:
    if name := function_name(node):
        _emit(ctx, EntityKind.FUNCTION, name, node)


def handle_field_declaration(node: Node, ctx: _Ctx) -> None:
    for name in field_declaration_names(node):
        _emit(ctx, EntityKind.FIELD, name, node)


def handle_struct_specifier(node: Node, ctx: _Ctx) -> None:
    if name := type_name(node):
        _emit(ctx, EntityKind.STRUCT, name, node)


def handle_class_specifier(node: Node, ctx: _Ctx) -> None:
    if name := type_name(node):
        _emit(ctx, EntityKind.CLASS, name, node)


def handle_enum_specifier(node: Node, ctx: _Ctx) -> None:
    if name := type_name(node):
        _emit(ctx, EntityKind.ENUM, name, node)


def handle_enumerator(node: Node, ctx: _Ctx) -> None:
    if name := enumerator_name(node):
        _emit(ctx, EntityKind.ENUMERATOR, name, node)


def handle_type_definition(node: Node, ctx: _Ctx) -> None:
    decl = node.child_by_field_name("declarator")
    if name := (declarator_name(decl) if decl is not None else None):
        _emit(ctx, EntityKind.TYPEDEF, name, node)


def handle_preproc_def(node: Node, ctx: _Ctx) -> None:
    if name := macro_name(node, ctx.source):
        _emit(ctx, EntityKind.MACRO, name, node)


def handle_namespace_definition(node: Node, ctx: _Ctx) -> None:
    name_node = node.child_by_field_name("name")
    name = (
        name_node.text.decode("utf-8", errors="replace")
        if name_node is not None and name_node.text
        else "anonymous"
    )
    _emit(ctx, EntityKind.NAMESPACE, name, node)

