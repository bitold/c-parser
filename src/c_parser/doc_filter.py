from __future__ import annotations

from typing import Iterable

from c_parser.models import Entity


class UndocumentedFilter:
    def filter(self, entities: Iterable[Entity], *, include_documented: bool) -> list[Entity]:
        if include_documented:
            return list(entities)
        return [e for e in entities if not e.has_documentation]

