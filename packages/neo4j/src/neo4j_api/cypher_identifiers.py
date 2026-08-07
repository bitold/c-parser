from __future__ import annotations

import re

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def require_cypher_identifier(name: str, *, kind: str) -> str:
    """Validate a Cypher label, relationship type, or property name."""
    if not _IDENT_RE.fullmatch(name):
        raise ValueError(f"Invalid Neo4j {kind}: {name!r}")
    return name
