from __future__ import annotations

import re
from collections import defaultdict

from c_parser.models import Entity, EntityKind, Relationship

_SPACE_RE = re.compile(r"\s+")


def is_function_definition(entity: Entity) -> bool:
    """True when ``entity`` looks like a function definition, not a declaration.
    """
    if entity.kind != EntityKind.FUNCTION:
        return False
    if entity.signature.rstrip().endswith(";"):
        return False
    return "{" in entity.body


def normalize_signature(signature: str) -> str:
    """
    Example:
        Input:  "   int   sum (int   a , int b ) ; "
        Output: "int sum(int a, int b)"
    """
    return _SPACE_RE.sub(" ", signature.strip().rstrip(";").strip())


def signatures_compatible(left: Entity, right: Entity) -> bool:
    """Whether two function entities share a compatible signature."""
    return normalize_signature(left.signature) == normalize_signature(right.signature)


class EntityRegistry:
    def __init__(self, entities: list[Entity]) -> None:
        self.entities = entities
        self.by_id: dict[str, Entity] = {}
        self.by_kind_and_name: dict[tuple[EntityKind, str], list[Entity]] = defaultdict(list)

        for entity in entities:
            self.by_id[entity.id] = entity
            self.by_kind_and_name[(entity.kind, entity.name)].append(entity)

    def find(self, kind: EntityKind, name: str) -> list[Entity]:
        return self.by_kind_and_name.get((kind, name), [])

    def function_definitions(self, name: str) -> list[Entity]:
        leaf = name.rsplit("::", 1)[-1]
        return [
            entity
            for entity in self.find(EntityKind.FUNCTION, leaf)
            if is_function_definition(entity)
        ]

    def resolve_function(self, name: str, *, source_path: str) -> Entity | None:
        """Найти сущность функции по имени вызова.

        Пример::

            registry.resolve_function("animals::Dog::bark", source_path="dog.cpp")
            # name="animals::Dog::bark" → leaf="bark", qualifier="animals::Dog"
            # вернёт Entity метода bark класса Dog, если оно однозначно

        ``name`` может быть квалифицированным (``animals::Dog::bark``): выделяются
        leaf (правый сегмент) и qualifier (всё слева от последнего ``::``).
        Сначала ищутся определения с именем leaf; при наличии qualifier
        оставляются только члены контейнера с этим именем. Предпочитается
        единственное определение в файле ``source_path``, иначе — единственное
        определение среди оставшихся. Если однозначного определения нет,
        рассматриваются все FUNCTION-кандидаты с именем leaf (включая
        объявления) с той же логикой qualifier; при неоднозначности
        возвращается ``None``.
        """
        leaf = name.rsplit("::", 1)[-1] # e.g. "animals::Dog::bark" -> "bark"
        qualifier = name.rsplit("::", 1)[0] if "::" in name else None # e.g. "animals::Dog::bark" -> "animals::Dog"

        # находим все определения функции с именем leaf
        definitions = self.function_definitions(leaf)
        if qualifier:
            # фильтруем определения функции, которые являются членами контейнера с именем qualifier
            scoped = [
                entity
                for entity in definitions
                if self._member_of_named_container(entity, qualifier)
            ]
            if len(scoped) == 1:
                return scoped[0]
            if scoped:
                definitions = scoped

        same_file = [entity for entity in definitions if entity.path == source_path]
        if len(same_file) == 1:
            return same_file[0]
        if len(definitions) == 1:
            return definitions[0]

        candidates = self.find(EntityKind.FUNCTION, leaf)
        if qualifier:
            scoped = [
                entity
                for entity in candidates
                if self._member_of_named_container(entity, qualifier)
            ]
            if len(scoped) == 1:
                return scoped[0]
            return None
        return candidates[0] if len(candidates) == 1 else None

    def resolve_class(self, name: str) -> Entity | None:
        """Resolve a class/struct base name, honoring ``ns::Base`` qualification."""
        leaf = name.rsplit("::", 1)[-1]
        qualifier = name.rsplit("::", 1)[0] if "::" in name else None
        matches = self.find(EntityKind.CLASS, leaf)
        if not matches:
            matches = self.find(EntityKind.STRUCT, leaf)
        if not matches:
            return None
        if qualifier:
            scoped = [
                entity
                for entity in matches
                if self._member_of_named_container(entity, qualifier)
            ]
            if len(scoped) == 1:
                return scoped[0]
            return None
        return matches[0] if len(matches) == 1 else None

    def _member_of_named_container(self, entity: Entity, qualifier: str) -> bool:
        """Проверить, является ли ``entity`` членом namespace/класса/struct с именем из ``qualifier``.

        Пример::

            # bark — метод класса Dog (bark -> MEMBER -> Dog)
            registry._member_of_named_container(bark_entity, "animals::Dog")
            # qualifier="animals::Dog" -> container_name="Dog" -> True

            registry._member_of_named_container(bark_entity, "animals::Cat")
            # container_name="Cat", MEMBER указывает на Dog -> False

        ``qualifier`` может быть вложенным (``animals::Dog``); для сравнения берётся
        только правый сегмент (``Dog``) и ищется связь MEMBER на контейнер
        с kind NAMESPACE/CLASS/STRUCT и таким ``name``.
        """
        container_name = qualifier.rsplit("::", 1)[-1]
        for relation in entity.relationships:
            if relation.type != Relationship.MEMBER:
                continue
            target = self.by_id.get(relation.target_id)
            if target is None:
                continue
            if (
                target.kind in {EntityKind.NAMESPACE, EntityKind.CLASS, EntityKind.STRUCT}
                and target.name == container_name
            ):
                return True
        return False
