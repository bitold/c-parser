from __future__ import annotations

from tree_sitter import Node

from c_parser.utils import is_doc_comment


def has_preceding_doc_comment(node: Node, source: bytes, *, strict: bool = False) -> bool:
    """Return True if declaration node has doc-style comments immediately before it."""
    sibling = node.prev_named_sibling
    while sibling is not None and sibling.type == "comment":
        if is_doc_comment(
            source[sibling.start_byte : sibling.end_byte].decode("utf-8", errors="replace"),
            strict=strict,
        ):
            return True
        sibling = sibling.prev_named_sibling
    return False
