from __future__ import annotations

from tree_sitter import Node

from c_parser.extractors.treesitter.utils import declarator_name, line_number, type_name
from c_parser.models import EntityKind, Relation, Relationship
from c_parser.utils import entity_id

_CONTAINER_TYPES = frozenset({"class_specifier", "struct_specifier", "namespace_definition"})
def enclosing_container_node(node: Node) -> Node | None:
    """Nearest enclosing class/struct/namespace for ``node`` (not ``node`` itself)."""
    parent = node.parent
    while parent is not None:
        if parent.type in _CONTAINER_TYPES:
            return parent
        parent = parent.parent
    return None


def enclosing_type_node(node: Node) -> Node | None:
    """Nearest enclosing class/struct for ``node`` (not ``node`` itself)."""
    parent = node.parent
    while parent is not None:
        if parent.type in {"class_specifier", "struct_specifier"}:
            return parent
        parent = parent.parent
    return None


def enclosing_enum_node(node: Node) -> Node | None:
    """Nearest enclosing enum_specifier for ``node`` (not ``node`` itself)."""
    parent = node.parent
    while parent is not None:
        if parent.type == "enum_specifier":
            return parent
        parent = parent.parent
    return None


def _container_name(container: Node) -> str | None:
    if container.type == "namespace_definition":
        name_node = container.child_by_field_name("name")
        if name_node is not None and name_node.text:
            return name_node.text.decode("utf-8", errors="replace")
        return "anonymous"
    return type_name(container)


def _container_kind(container: Node) -> EntityKind:
    return {
        "class_specifier": EntityKind.CLASS,
        "namespace_definition": EntityKind.NAMESPACE,
        "struct_specifier": EntityKind.STRUCT,
    }[container.type]


def member_of_relation(node: Node, path: str) -> Relation | None:
    """MEMBER relation to nearest class/struct/namespace container."""
    container = enclosing_container_node(node)
    if container is None:
        return None
    name = _container_name(container)
    if name is None:
        return None
    return Relation(
        type=Relationship.MEMBER,
        target_id=entity_id(
            path,
            _container_kind(container).value,
            name,
            line_number(container),
        ),
    )


def member_of_enum_relation(node: Node, path: str) -> Relation | None:
    """MEMBER relation from enumerator to its enum."""
    container = enclosing_enum_node(node)
    if container is None:
        return None
    name = type_name(container)
    if name is None:
        return None
    return Relation(
        type=Relationship.MEMBER,
        target_id=entity_id(
            path,
            EntityKind.ENUM.value,
            name,
            line_number(container),
        ),
    )


def field_declaration_names(node: Node) -> list[str]:
    """Field names declared by a ``field_declaration`` node."""
    names: list[str] = []
    skip = {
        "primitive_type",
        "type_identifier",
        "sized_type_specifier",
        "struct_specifier",
        "enum_specifier",
        "class_specifier",
        "union_specifier",
        "type_qualifier",
        "storage_class_specifier",
        "access_specifier",
        "attribute_specifier",
        "attribute_declaration",
        "virtual",
        "explicit_function_specifier",
    }
    for child in node.children:
        if not child.is_named or child.type in skip:
            continue
        if child.type == "field_identifier":
            if child.text:
                names.append(child.text.decode("utf-8", errors="replace"))
            continue
        name = declarator_name(child)
        if name:
            names.append(name)
    return names


def enumerator_name(node: Node) -> str | None:
    """Name of an ``enumerator`` node."""
    name_node = node.child_by_field_name("name")
    if name_node is not None and name_node.text:
        return name_node.text.decode("utf-8", errors="replace")
    for child in node.children:
        if child.type == "identifier" and child.text:
            return child.text.decode("utf-8", errors="replace")
    return None


def callee_name(function_node: Node) -> str | None:
    """Resolve the callee name from a ``call_expression``'s ``function`` child.

    Supports plain identifiers, qualified names (``ns::f``), field/member
    access (``obj.f`` / ``this->f``), and one level of parentheses.
    """
    node = function_node
    if node.type == "parenthesized_expression":
        inner = next((c for c in node.children if c.is_named), None)
        if inner is None:
            return None
        node = inner

    if node.type == "identifier" and node.text:
        return node.text.decode("utf-8", errors="replace")

    if node.type == "qualified_identifier" and node.text:
        # Keep qualification so resolvers can disambiguate on collisions.
        return node.text.decode("utf-8", errors="replace").lstrip(":")

    if node.type == "field_expression":
        field = node.child_by_field_name("field")
        if field is not None and field.text:
            return field.text.decode("utf-8", errors="replace")

    return None


def base_class_names(class_node: Node) -> list[str]:
    """Base class type names from a ``class_specifier``'s ``base_class_clause``.

    Qualified bases keep their qualification (e.g. ``ns::Base``) so the
    resolver can disambiguate when multiple classes share a leaf name.
    """
    names: list[str] = []
    for child in class_node.children:
        if child.type != "base_class_clause":
            continue
        for base in child.children:
            if base.type == "type_identifier" and base.text:
                names.append(base.text.decode("utf-8", errors="replace"))
            elif base.type == "qualified_identifier" and base.text:
                names.append(
                    base.text.decode("utf-8", errors="replace").lstrip(":")
                )
    return names
