from __future__ import annotations

from pathlib import Path

import pytest

from c_parser.extractors import TreeSitterExtractor
from c_parser.models import EntityKind, Relationship

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def extractor() -> TreeSitterExtractor:
    return TreeSitterExtractor()


def _names(entities, kind: EntityKind | None = None) -> set[str]:
    if kind is None:
        return {e.name for e in entities}
    return {e.name for e in entities if e.kind == kind}


def entities_by_name(entities, name: str):
    return next(e for e in entities if e.name == name)


def rels_of(entity, rel_type: Relationship):
    return [r for r in entity.relationships if r.type == rel_type]


def extract_entities(
    extractor: TreeSitterExtractor,
    root: Path,
    **options,
):
    entities = []
    extractor.extract(root, entities.append, **options)
    return entities


def test_extracts_undocumented_c_entities(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "undocumented.c")

    assert _names(entities, EntityKind.FILE) == {"undocumented.c"}
    assert _names(entities, EntityKind.FUNCTION) == {"add", "foo", "bar", "baz"}
    assert _names(entities, EntityKind.STRUCT) == {"Point"}
    assert _names(entities, EntityKind.FIELD) == {"x", "y"}
    assert _names(entities, EntityKind.TYPEDEF) == {"size_t_alias"}
    assert _names(entities, EntityKind.MACRO) == {"MAX_ITEMS"}
    assert all(not e.has_documentation for e in entities)


def test_skips_documented_entities_in_mixed_file(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "mixed.c")

    names = _names(entities)
    assert "documented_add" not in names
    assert "DocumentedPoint" not in names
    assert "documented_size_t" not in names
    assert "DOCUMENTED_MAX" not in names

    assert "undocumented_sub" in names
    assert entities_by_name(entities, "undocumented_sub").has_documentation is False


def test_extracts_cpp_entities(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "undocumented.cpp")

    assert _names(entities, EntityKind.CLASS) == {"Base", "Widget"}
    assert _names(entities, EntityKind.NAMESPACE) == {"app"}
    assert _names(entities, EntityKind.ENUM) == {"Mode"}
    assert _names(entities, EntityKind.ENUMERATOR) == {"On", "Off"}
    assert _names(entities, EntityKind.TYPEDEF) == {"WidgetPtr"}
    assert _names(entities, EntityKind.MACRO) == {"WIDGET_VERSION"}
    assert _names(entities, EntityKind.FIELD) == {"id_", "value_"}


def test_cpp_mixed_documentation(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "mixed.cpp")

    names = _names(entities)
    assert "DocumentedWidget" not in names
    assert "UndocumentedGadget" in names


def test_entity_fields(extractor: TreeSitterExtractor):
    path = FIXTURES / "undocumented.c"
    entities = extract_entities(extractor, path)
    add = entities_by_name(entities, "add")

    assert add.kind == EntityKind.FUNCTION
    assert add.language.value == "c"
    assert add.path == str(path)
    assert add.start_line >= 1
    assert add.end_line >= add.start_line
    assert "int add" in add.signature
    assert "return a + b" in add.body
    assert add.id == f"{path}::function::add::{add.start_line}"
    assert add.relationships == []


def test_member_relationship_for_class_method(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "undocumented.cpp")

    widget = entities_by_name(entities, "Widget")
    value = entities_by_name(entities, "value")

    member = rels_of(value, Relationship.MEMBER)
    assert len(member) == 1
    assert member[0].target_id == widget.id


def test_field_member_and_struct_defines(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "undocumented.c")

    point = entities_by_name(entities, "Point")
    x = entities_by_name(entities, "x")

    assert rels_of(x, Relationship.MEMBER)[0].target_id == point.id
    define_targets = {r.target_id for r in rels_of(point, Relationship.DEFINES)}
    assert x.id in define_targets


def test_calls_same_file(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "undocumented.c")

    foo = entities_by_name(entities, "foo")
    bar = entities_by_name(entities, "bar")
    baz = entities_by_name(entities, "baz")

    call_targets = {r.target_id for r in rels_of(foo, Relationship.CALLS)}
    assert call_targets == {bar.id, baz.id}


def test_inherits_and_enumerator_member(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "undocumented.cpp")

    base = entities_by_name(entities, "Base")
    widget = entities_by_name(entities, "Widget")
    mode = entities_by_name(entities, "Mode")
    on = entities_by_name(entities, "On")
    app = entities_by_name(entities, "app")
    run = next(
        e
        for e in entities
        if e.name == "run"
        and e.kind == EntityKind.FUNCTION
        and any(r.type == Relationship.MEMBER and r.target_id == app.id for r in e.relationships)
    )

    inherits = rels_of(widget, Relationship.INHERITS)
    assert len(inherits) == 1
    assert inherits[0].target_id == base.id

    assert rels_of(on, Relationship.MEMBER)[0].target_id == mode.id
    assert on.id in {r.target_id for r in rels_of(mode, Relationship.DEFINES)}

    assert rels_of(run, Relationship.MEMBER)[0].target_id == app.id
    assert run.id in {r.target_id for r in rels_of(app, Relationship.DEFINES)}


def test_cpp_method_calls(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "undocumented.cpp")

    run = entities_by_name(entities, "run")
    # method run() inside Widget, not namespace app::run
    run = next(e for e in entities if e.name == "run" and e.kind == EntityKind.FUNCTION and any(
        r.type == Relationship.MEMBER and "Widget" in r.target_id for r in e.relationships
    ))
    helper = entities_by_name(entities, "helper")
    assert helper.id in {r.target_id for r in rels_of(run, Relationship.CALLS)}


def test_file_entity_emitted(extractor: TreeSitterExtractor):
    path = FIXTURES / "undocumented.c"
    entities = extract_entities(extractor, path)

    file_ent = next(e for e in entities if e.kind == EntityKind.FILE)
    assert file_ent.name == "undocumented.c"
    assert file_ent.path == str(path)
    assert file_ent.signature == str(path)
    assert file_ent.id == f"{path}::file::undocumented.c::1"


def test_file_and_function_contract_relations(extractor: TreeSitterExtractor):
    root = Path(__file__).resolve().parents[1] / "testdata" / "simple_app"
    all_entities = extract_entities(extractor, root)

    files = {e.path: e for e in all_entities if e.kind == EntityKind.FILE}
    app_path = str(root / "app.c")
    math_source_path = str(root / "math_utils.c")
    math_header_path = str(root / "math_utils.h")
    string_header_path = str(root / "string_utils.h")
    app = files[app_path]
    include_targets = {r.target_id for r in rels_of(app, Relationship.INCLUDES)}
    assert files[math_header_path].id in include_targets
    assert files[string_header_path].id in include_targets
    # system include <stdio.h> is not in the corpus
    assert all("stdio" not in tid for tid in include_targets)

    add_decl = next(
        e
        for e in all_entities
        if e.name == "add"
        and e.kind == EntityKind.FUNCTION
        and e.path.endswith("math_utils.h")
    )
    add_def = next(
        e
        for e in all_entities
        if e.name == "add"
        and e.kind == EntityKind.FUNCTION
        and e.path.endswith("math_utils.c")
    )
    assert add_decl.id in {
        relation.target_id
        for relation in rels_of(
            files[math_header_path],
            Relationship.DECLARES,
        )
    }
    assert add_def.id in {
        relation.target_id
        for relation in rels_of(
            files[math_source_path],
            Relationship.DEFINES,
        )
    }
    assert add_decl.id in {
        relation.target_id
        for relation in rels_of(add_def, Relationship.IMPLEMENTS)
    }
    assert files[math_header_path].id in {
        relation.target_id
        for relation in rels_of(
            files[math_source_path],
            Relationship.IMPLEMENTS,
        )
    }


def test_calls_are_resolved_across_files(extractor: TreeSitterExtractor):
    root = Path(__file__).resolve().parents[1] / "testdata" / "simple_app"
    entities = extract_entities(extractor, root)

    main = entities_by_name(entities, "main")
    targets_by_id = {entity.id: entity for entity in entities}
    callees = {
        targets_by_id[rel.target_id].name
        for rel in rels_of(main, Relationship.CALLS)
    }

    assert callees == {
        "add",
        "distance_sq",
        "print_point",
        "str_copy",
        "str_len",
    }


def test_entity_ids_include_kind(extractor: TreeSitterExtractor):
    root = Path(__file__).resolve().parents[1] / "testdata" / "simple_app"
    entities = extract_entities(extractor, root)
    points = [entity for entity in entities if entity.name == "Point"]

    assert {entity.kind for entity in points} == {
        EntityKind.STRUCT,
        EntityKind.TYPEDEF,
    }
    assert len({entity.id for entity in points}) == 2


def test_simple_app_is_weakly_connected(extractor: TreeSitterExtractor):
    root = Path(__file__).resolve().parents[1] / "testdata" / "simple_app"
    entities = extract_entities(extractor, root)
    by_id = {entity.id: entity for entity in entities}
    adjacency = {entity.id: set() for entity in entities}

    for entity in entities:
        for relation in entity.relationships:
            adjacency[entity.id].add(relation.target_id)
            adjacency[relation.target_id].add(entity.id)

    visited: set[str] = set()
    pending = [entities[0].id]
    while pending:
        entity_id = pending.pop()
        if entity_id in visited:
            continue
        visited.add(entity_id)
        pending.extend(adjacency[entity_id] - visited)

    assert visited == set(by_id)


def test_qualified_and_member_calls(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "relations.cpp")
    by_id = {entity.id: entity for entity in entities}

    caller = next(
        e
        for e in entities
        if e.name == "caller" and e.kind == EntityKind.FUNCTION
    )
    log_fn = next(
        e
        for e in entities
        if e.name == "log" and e.kind == EntityKind.FUNCTION
    )
    assert log_fn.id in {r.target_id for r in rels_of(caller, Relationship.CALLS)}

    run = next(
        e
        for e in entities
        if e.name == "run" and e.kind == EntityKind.FUNCTION
    )
    helper = next(
        e
        for e in entities
        if e.name == "helper"
        and e.kind == EntityKind.FUNCTION
        and any(r.type == Relationship.MEMBER and "Widget" in r.target_id for r in e.relationships)
    )
    assert helper.id in {r.target_id for r in rels_of(run, Relationship.CALLS)}

    use_widget = entities_by_name(entities, "use_widget")
    call_names = {
        by_id[r.target_id].name for r in rels_of(use_widget, Relationship.CALLS)
    }
    assert "run" in call_names
    assert "log" in call_names


def test_inherits_qualified_base_under_name_collision(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "relations.cpp")

    child = entities_by_name(entities, "Child")
    util_ns = entities_by_name(entities, "util")
    util_base = next(
        e
        for e in entities
        if e.name == "Base"
        and e.kind == EntityKind.CLASS
        and any(
            r.type == Relationship.MEMBER and r.target_id == util_ns.id
            for r in e.relationships
        )
    )
    inherits = rels_of(child, Relationship.INHERITS)
    assert len(inherits) == 1
    assert inherits[0].target_id == util_base.id


def test_implements_requires_compatible_signature(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "implements_mismatch")

    decl = next(
        e
        for e in entities
        if e.name == "foo" and e.path.endswith("api.h")
    )
    definition = next(
        e
        for e in entities
        if e.name == "foo" and e.path.endswith("api.c")
    )
    assert rels_of(definition, Relationship.IMPLEMENTS) == []
    assert decl.id not in {
        r.target_id for r in rels_of(definition, Relationship.IMPLEMENTS)
    }

    files = {e.name: e for e in entities if e.kind == EntityKind.FILE}
    assert rels_of(files["api.c"], Relationship.IMPLEMENTS) == []



def test_file_implements_requires_matching_functions(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "stem_only")
    files = {e.name: e for e in entities if e.kind == EntityKind.FILE}
    source = files["widget.c"]
    assert rels_of(source, Relationship.IMPLEMENTS) == []


def test_angled_include_does_not_basename_fallback(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "include_angled_basename")
    files = {e.name: e for e in entities if e.kind == EntityKind.FILE}
    main = files["main.c"]
    assert rels_of(main, Relationship.INCLUDES) == []


def test_quoted_include_resolves_relative_path(extractor: TreeSitterExtractor):
    entities = extract_entities(extractor, FIXTURES / "include_trap")
    files = {e.path: e for e in entities if e.kind == EntityKind.FILE}
    user = next(e for e in files.values() if e.name == "user.c")
    local_util = next(
        e for e in files.values() if e.name == "util.h" and e.path.endswith("/a/util.h")
    )
    include_targets = {r.target_id for r in rels_of(user, Relationship.INCLUDES)}
    assert local_util.id in include_targets

    main = next(e for e in files.values() if e.name == "main.c")
    # <util.h> must not guess either corpus util.h via basename
    assert rels_of(main, Relationship.INCLUDES) == []
