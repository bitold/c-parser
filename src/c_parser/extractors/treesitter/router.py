from __future__ import annotations

from tree_sitter import Node

from c_parser.extractors.treesitter.core import _Ctx, _is_function_declaration
from c_parser.extractors.treesitter.handlers import (
    handle_class_specifier,
    handle_enum_specifier,
    handle_enumerator,
    handle_field_declaration,
    handle_function_declaration,
    handle_function_definition,
    handle_namespace_definition,
    handle_preproc_def,
    handle_struct_specifier,
    handle_type_definition,
)


def route_node(node: Node, ctx: _Ctx) -> None:
    """Dispatch `node` to an appropriate handler based on `node.type`."""

    match node.type:
        case "function_definition":
            handle_function_definition(node, ctx)

        case "declaration" if _is_function_declaration(node):
            handle_function_declaration(node, ctx)

        case "field_declaration":
            handle_field_declaration(node, ctx)

        case "struct_specifier":
            handle_struct_specifier(node, ctx)

        case "class_specifier":
            handle_class_specifier(node, ctx)

        case "enum_specifier":
            handle_enum_specifier(node, ctx)

        case "enumerator":
            handle_enumerator(node, ctx)

        case "type_definition":
            handle_type_definition(node, ctx)

        case "preproc_def" | "preproc_function_def":
            handle_preproc_def(node, ctx)

        case "namespace_definition":
            handle_namespace_definition(node, ctx)

