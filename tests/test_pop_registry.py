from pop.registry import (
    list_persona_ids,
    list_personas,
    load_persona_by_id,
    normalize_persona_ref,
    resolve_persona,
)


def test_list_personas():
    personas = list_personas()
    assert isinstance(personas, list)


def test_list_persona_ids():
    persona_ids = list_persona_ids()
    assert isinstance(persona_ids, list)
    assert "marketing_manager_v1" in persona_ids


def test_normalize_persona_ref():
    assert normalize_persona_ref("marketing_manager_v1") == "marketing_manager_v1"
    assert normalize_persona_ref("pop:marketing_manager_v1") == "marketing_manager_v1"


def test_resolve_persona_by_pop_id():
    path = resolve_persona("pop:marketing_manager_v1")
    assert path is not None
    assert path.name == "marketing_manager.json"


def test_load_persona_by_pop_id():
    persona = load_persona_by_id("pop:marketing_manager_v1")
    assert persona.persona_id == "marketing_manager_v1"
