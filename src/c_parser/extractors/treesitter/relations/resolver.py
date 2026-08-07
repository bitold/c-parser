from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from c_parser.extractors.treesitter.registry import (
    EntityRegistry,
    is_function_definition,
    signatures_compatible,
)
from c_parser.extractors.treesitter.relations.facts import RelationFacts
from c_parser.models import Entity, EntityKind, Relation, Relationship


class RelationResolver:
    """Resolve collected facts against the complete in-memory entity registry."""

    def resolve(
        self,
        registry: EntityRegistry,
        facts: RelationFacts,
    ) -> None:
        self._resolve_direct(registry, facts)
        self._resolve_named(registry, facts)
        included_files = self._resolve_includes(registry, facts)
        self._resolve_file_ownership(registry, facts)
        self._resolve_function_implementations(registry)
        self._resolve_file_implementations(registry, included_files)

    def prune(self, entities: list[Entity]) -> None:
        ids = {entity.id for entity in entities}
        for entity in entities:
            entity.relationships[:] = [
                relation
                for relation in entity.relationships
                if relation.target_id in ids
            ]

    def _resolve_direct(
        self,
        registry: EntityRegistry,
        facts: RelationFacts,
    ) -> None:
        for fact in facts.direct:
            source = registry.by_id.get(fact.source_id)
            target = registry.by_id.get(fact.target_id)
            if source is None or target is None:
                continue

            _attach(source, fact.type, target.id)
            if fact.type == Relationship.MEMBER:
                _attach(target, Relationship.DEFINES, source.id)

    def _resolve_named(
        self,
        registry: EntityRegistry,
        facts: RelationFacts,
    ) -> None:
        for fact in facts.named:
            source = registry.by_id.get(fact.source_id)
            if source is None:
                continue

            target: Entity | None = None
            if fact.type == Relationship.CALLS:
                target = registry.resolve_function(
                    fact.target_name,
                    source_path=source.path,
                )
            elif fact.type == Relationship.INHERITS:
                target = registry.resolve_class(fact.target_name)

            if target is None or target.id == source.id:
                continue
            _attach(source, fact.type, target.id)

    def _resolve_includes(
        self,
        registry: EntityRegistry,
        facts: RelationFacts,
    ) -> list[tuple[Entity, Entity]]:
        files_by_path = {
            _normalize_path(entity.path): entity
            for entity in registry.entities
            if entity.kind == EntityKind.FILE
        }
        files_by_basename: dict[str, list[Entity]] = defaultdict(list)
        for entity in files_by_path.values():
            files_by_basename[Path(entity.path).name].append(entity)

        resolved: list[tuple[Entity, Entity]] = []
        seen: set[tuple[str, str]] = set()
        for fact in facts.includes:
            source = files_by_path.get(_normalize_path(fact.source_path))
            if source is None:
                continue

            target: Entity | None = None
            if fact.angled:
                # System-style includes: never resolve relative to the source
                # file and never guess by basename (common names like util.h).
                # Only accept a unique corpus path ending with the include's
                # multi-component path (e.g. <proj/util.h>).
                included = Path(fact.included_path)
                if len(included.parts) >= 2:
                    needle = included.as_posix()
                    matches = [
                        entity
                        for path, entity in files_by_path.items()
                        if path == needle or path.endswith("/" + needle)
                    ]
                    if len(matches) == 1:
                        target = matches[0]
            else:
                included_path = _normalize_path(
                    str(Path(fact.source_path).parent / fact.included_path)
                )
                target = files_by_path.get(included_path)
                if target is None:
                    # Bare quoted filename only: unique basename fallback.
                    included = Path(fact.included_path)
                    if len(included.parts) == 1:
                        matches = files_by_basename.get(included.name, [])
                        if len(matches) == 1:
                            target = matches[0]

            if target is None or target.id == source.id:
                continue
            _attach(source, Relationship.INCLUDES, target.id)
            pair = (source.id, target.id)
            if pair not in seen:
                resolved.append((source, target))
                seen.add(pair)

        return resolved

    def _resolve_file_ownership(
        self,
        registry: EntityRegistry,
        facts: RelationFacts,
    ) -> None:
        files_by_path = {
            _normalize_path(entity.path): entity
            for entity in registry.entities
            if entity.kind == EntityKind.FILE
        }
        nested_ids = {
            fact.source_id
            for fact in facts.direct
            if fact.type == Relationship.MEMBER
        }

        for entity in registry.entities:
            if entity.kind == EntityKind.FILE or entity.id in nested_ids:
                continue

            file_entity = files_by_path.get(_normalize_path(entity.path))
            if file_entity is None:
                continue

            relation_type = (
                Relationship.DECLARES
                if entity.kind == EntityKind.FUNCTION
                and not is_function_definition(entity)
                else Relationship.DEFINES
            )
            _attach(file_entity, relation_type, entity.id)

    def _resolve_function_implementations(
        self,
        registry: EntityRegistry,
    ) -> None:
        for entity in registry.entities:
            if (
                entity.kind != EntityKind.FUNCTION
                or is_function_definition(entity)
            ):
                continue

            definitions = [
                definition
                for definition in registry.function_definitions(entity.name)
                if signatures_compatible(entity, definition)
            ]
            if len(definitions) == 1:
                _attach(
                    definitions[0],
                    Relationship.IMPLEMENTS,
                    entity.id,
                )

    def _resolve_file_implementations(
        self,
        registry: EntityRegistry,
        included_files: list[tuple[Entity, Entity]],
    ) -> None:
        declarations_by_path: dict[str, list[Entity]] = defaultdict(list)
        definitions_by_path: dict[str, list[Entity]] = defaultdict(list)
        for entity in registry.entities:
            if entity.kind != EntityKind.FUNCTION:
                continue
            path = _normalize_path(entity.path)
            if is_function_definition(entity):
                definitions_by_path[path].append(entity)
            else:
                declarations_by_path[path].append(entity)

        implementation_extensions = {".c", ".cc", ".cpp", ".cxx"}
        header_extensions = {".h", ".hh", ".hpp", ".hxx"}
        for source, target in included_files:
            source_path = Path(source.path)
            target_path = Path(target.path)
            if (
                source_path.suffix.lower() not in implementation_extensions
                or target_path.suffix.lower() not in header_extensions
            ):
                continue

            # Require at least one signature-compatible name pair — stem match
            # alone (or same-name incompatible overloads) must not over-assert.
            definitions = definitions_by_path[_normalize_path(source.path)]
            declarations = declarations_by_path[_normalize_path(target.path)]
            has_evidence = any(
                definition.name == declaration.name
                and signatures_compatible(definition, declaration)
                for definition in definitions
                for declaration in declarations
            )
            if not has_evidence:
                continue

            _attach(source, Relationship.IMPLEMENTS, target.id)


def _attach(
    source: Entity,
    relation_type: Relationship,
    target_id: str,
) -> None:
    relation = Relation(type=relation_type, target_id=target_id)
    if relation not in source.relationships:
        source.relationships.append(relation)


def _normalize_path(path: str) -> str:
    return Path(os.path.normpath(path)).as_posix()
