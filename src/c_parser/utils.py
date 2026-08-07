from __future__ import annotations

import re
from pathlib import Path

from c_parser.models import Language

CPP_EXTENSIONS = {".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"}
C_EXTENSIONS = {".c", ".h"}

_DOC_BLOCK_RE = re.compile(r"^\s*/\*\*")  # /** ... */
_DOC_LINE_RE = re.compile(r"^\s*///")  # /// ...
_DOC_BANG_RE = re.compile(r"^\s*//!")  # //! ...


def is_doc_comment(text: str, *, strict: bool = False) -> bool:
    if _DOC_BLOCK_RE.match(text):
        return True
    if _DOC_LINE_RE.match(text):
        return True
    if not strict and _DOC_BANG_RE.match(text):
        return True
    return False


def language_for_path(path: str) -> Language:
    suffix = Path(path).suffix.lower()
    if suffix in CPP_EXTENSIONS:
        return Language.CPP
    return Language.C


def entity_id(path: str, kind: str, name: str, start_line: int) -> str:
    return f"{path}::{kind}::{name}::{start_line}"
