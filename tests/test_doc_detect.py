from __future__ import annotations

from c_parser.utils import is_doc_comment


def test_doc_block_comment():
    assert is_doc_comment("/** docs */")
    assert not is_doc_comment("/* regular */")


def test_doc_line_comment():
    assert is_doc_comment("/// docs")
    assert not is_doc_comment("// regular")


def test_doc_bang_comment():
    assert is_doc_comment("//! docs")
    assert not is_doc_comment("//! docs", strict=True)
