from __future__ import annotations

from pathlib import Path
from typing import Iterator

SOURCE_EXTENSIONS = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"}


def iter_source_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        if root.suffix.lower() in SOURCE_EXTENSIONS:
            yield root
        return

    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS:
            yield path
