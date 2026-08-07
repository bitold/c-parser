from __future__ import annotations

from typing import Protocol

from c_parser.models import Entity


class Sink(Protocol):
    def write(self, entity: Entity) -> None:
        ...

    def close(self) -> None:
        ...
