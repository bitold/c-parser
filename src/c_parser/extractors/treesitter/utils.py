from __future__ import annotations

from tree_sitter import Node


def require_node_type(node: Node, *expected: str) -> Node:
    """Raise ValueError unless ``node.type`` is one of ``expected``."""
    if node.type not in expected:
        want = expected[0] if len(expected) == 1 else expected
        raise ValueError(f"Expected {want}, got {node.type}")
    return node


def node_text(source: bytes, node: Node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def line_number(node: Node) -> int:
    """
    Номер строки для указанного узла.

    Прибавляет 1 к номеру от tree-sitter, так как нумерация в tree-sitter начинается с 0.
    """
    return node.start_point[0] + 1


def end_line_number(node: Node) -> int:
    """
    Номер строки для конца указанного узла.

    Прибавляет 1 к номеру от tree-sitter, так как нумерация в tree-sitter начинается с 0.
    """
    return node.end_point[0] + 1


def declarator_name(node: Node) -> str | None:
    if node.type in {"identifier", "type_identifier", "field_identifier"}:
        return node.text.decode("utf-8", errors="replace") if node.text else None

    for child in node.children:
        if child.is_named:
            name = declarator_name(child)
            if name:
                return name
    return None


def function_name(node: Node) -> str | None:
    require_node_type(node, "function_definition", "declaration")
    decl = node.child_by_field_name("declarator")
    if decl is None:
        return None
    return declarator_name(decl)


def type_name(node: Node) -> str | None:
    """
    Имя типа из grammar-field ``name`` у узла specifier'а.

    Читает ``node.child_by_field_name("name")`` — так tree-sitter-c/cpp
    помечает идентификатор у ``struct`` / ``class`` / ``enum``.

    Args:
        node: Обычно ``struct_specifier``, ``class_specifier`` или
            ``enum_specifier``.

    Returns:
        Текст имени (например ``"Point"``), либо ``None``, если field
        ``name`` отсутствует (анонимный тип) или пуст.

    Пример::

        struct Point { int x; };   # struct_specifier → "Point"
        class Widget {};           # class_specifier → "Widget"
        enum Color { R, G };       # enum_specifier → "Color"
        struct { int z; } g;       # анонимный struct_specifier → None
        typedef int alias_t;       # type_definition: field name нет → None
    """
    require_node_type(node, "struct_specifier", "class_specifier", "enum_specifier")
    name_node = node.child_by_field_name("name")
    if name_node is not None and name_node.text:
        return name_node.text.decode("utf-8", errors="replace")
    return None


def macro_name(node: Node, source: bytes) -> str | None:
    """Имя макроса из grammar-field ``name`` у ``preproc_def`` / ``preproc_function_def``."""
    require_node_type(node, "preproc_def", "preproc_function_def")
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    return node_text(source, name_node)


def signature_for_function(node: Node, source: bytes) -> str:
    require_node_type(node, "function_definition")
    body = node.child_by_field_name("body")
    full = node_text(source, node)
    if body is None:
        return full
    body_text = node_text(source, body)
    if full.endswith(body_text):
        return full[: -len(body_text)].rstrip()
    return full
