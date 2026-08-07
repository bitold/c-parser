from __future__ import annotations

from pathlib import Path
from typing import Callable

from tree_sitter import Language as TSLanguage, Node, Parser
from tree_sitter_c import language as c_language
from tree_sitter_cpp import language as cpp_language

from c_parser.doc_filter import UndocumentedFilter
from c_parser.extractors.treesitter.core import _Ctx
from c_parser.extractors.treesitter.mappers import make_file_entity
from c_parser.extractors.treesitter.registry import EntityRegistry
from c_parser.extractors.treesitter.relations import RelationPipeline
from c_parser.extractors.treesitter.router import route_node
from c_parser.models import Entity, Language
from c_parser.utils import language_for_path
from c_parser.walk import iter_source_files

class TreeSitterExtractor:
    def __init__(self) -> None:
        self._parsers: dict[Language, Parser] = {}
        self._languages: dict[Language, TSLanguage] = {
            Language.C: TSLanguage(c_language()),
            Language.CPP: TSLanguage(cpp_language()),
        }
        self._filter = UndocumentedFilter()

    def _parser_for(self, language: Language) -> Parser:
        if language not in self._parsers:
            self._parsers[language] = Parser(self._languages[language])
        return self._parsers[language]

    def extract(
        self,
        root: Path,
        emit: Callable[[Entity], None],
        *,
        strict_doc_comments: bool = False,
        include_documented: bool = False,
    ) -> None:
        """Extract and globally resolve all supported sources below ``root``."""
        entities: list[Entity] = []
        relations = RelationPipeline()

        for file_path in iter_source_files(Path(root)):
            ctx = self._extract_file(
                file_path,
                relations,
                strict_doc_comments=strict_doc_comments,
            )
            entities.extend(ctx.entities)

        registry = EntityRegistry(entities)
        relations.resolve(registry)

        filtered = self._filter.filter(
            registry.entities,
            include_documented=include_documented,
        )
        relations.prune(filtered)
        for entity in filtered:
            emit(entity)

    def _extract_file(
        self,
        file_path: Path,
        relations: RelationPipeline,
        *,
        strict_doc_comments: bool,
    ) -> _Ctx:
        path = str(file_path)
        source = file_path.read_text(encoding="utf-8", errors="replace")
        language = language_for_path(path)
        ctx = _Ctx(
            source=source.encode("utf-8"),
            path=path,
            language=language,
            strict_doc_comments=strict_doc_comments,
        )
        root = self._parser_for(language).parse(ctx.source).root_node
        ctx.entities.append(make_file_entity(path=path, language=language, source=source))
        self._walk(root, ctx, relations)
        return ctx

    def _walk(
        self,
        node: Node,
        ctx: _Ctx,
        relations: RelationPipeline,
    ) -> None:
        # Мгновенно маршрутизируем узел в соответствующий handler,
        # а рекурсия остаётся в этом методе.
        route_node(node, ctx)
        relations.handle(node, ctx)

        for child in node.children:
            if child.is_named:
                self._walk(child, ctx, relations)
