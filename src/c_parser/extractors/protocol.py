from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

from c_parser.models import Entity


class EntityExtractor(Protocol):
    def extract(
        self,
        root: Path,
        emit: Callable[[Entity], None],
        *,
        strict_doc_comments: bool = False,
        include_documented: bool = False,
    ) -> None:
        ...
