from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Neo4jConfig:
    """Connection settings for a Neo4j database."""

    uri: str
    username: str
    password: str
    database: str
