from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from c_parser.models import Entity


class JsonlSink:
    def __init__(self, output: TextIO) -> None:
        self._output = output

    @classmethod
    def from_path(cls, path: Path) -> JsonlSink:
        """
        Создает новый JSONL sink, который записывает в указанный файл.
        
        Args:
            path: Путь к файлу, в который будет записываться.

        Returns:
            Новый JSONL sink.
        """
        return cls(path.open("w", encoding="utf-8"))

    def write(self, entity: Entity) -> None:
        self._output.write(json.dumps(entity.to_dict(), ensure_ascii=False) + "\n")

    def close(self) -> None:
        self._output.close()
