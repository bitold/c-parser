from __future__ import annotations

from tree_sitter import Node

from c_parser.extractors.treesitter.core import _Ctx
from c_parser.extractors.treesitter.registry import EntityRegistry
from c_parser.extractors.treesitter.relations.facts import RelationFacts
from c_parser.extractors.treesitter.relations.handler import RelationHandler
from c_parser.extractors.treesitter.relations.resolver import RelationResolver
from c_parser.models import Entity


class RelationPipeline:
    """Collect relation facts during AST traversal and resolve them afterwards."""

    def __init__(self) -> None:
        self._facts = RelationFacts()
        self._handler = RelationHandler()
        self._resolver = RelationResolver()

    def handle(self, node: Node, ctx: _Ctx) -> None:
        self._handler.handle(node, ctx, self._facts)

    def resolve(self, registry: EntityRegistry) -> None:
        self._resolver.resolve(registry, self._facts)

    def prune(self, entities: list[Entity]) -> None:
        self._resolver.prune(entities)
