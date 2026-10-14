import json
from datetime import UTC, datetime
from pathlib import Path

from pop_cockpit.config import AppConfig
from pop_cockpit.persona import (
    export_persona_core,
    format_persona_core_summary,
    rebuild_persona_core,
    show_persona_core,
)
from pop_cockpit.schemas import DailyPersonaSnapshot, DateRange
from pop_cockpit.storage import (
    ensure_runtime,
    get_connection,
    get_current_persona_core,
    insert_daily_persona_snapshot,
)


def make_test_config(tmp_path: Path) -> AppConfig:
    data_dir = tmp_path / "data"
    return AppConfig(
        root_dir=tmp_path,
        data_dir=data_dir,
        raw_logs_dir=data_dir / "raw_logs",
        daily_notes_dir=data_dir / "daily_notes",
        persona_core_dir=data_dir / "persona_core",
        sessions_dir=data_dir / "sessions",
        database_path=data_dir / "pop_persona.db",
    )


def seed_daily_snapshot(
    config: AppConfig,
    snapshot_id: str,
    date_value: str,
    *,
    snapshot_scope: str = "all",
    goal_priority: list[str] | None = None,
    current_focus: list[str] | None = None,
    decision_style: str = "",
    risk_profile: str = "",
    recurring_topics: list[str] | None = None,
    stable_biases: list[str] | None = None,
    emotional_signals: list[str] | None = None,
    new_traits: list[str] | None = None,
    important_decisions: list[str] | None = None,
    confidence_notes: list[str] | None = None,
) -> None:
    ensure_runtime(config)
    snapshot = DailyPersonaSnapshot(
        id=snapshot_id,
        date_range=DateRange(date_from=date_value, date_to=date_value),
        source_record_ids=[f"imp_{snapshot_id}"],
        goal_priority=goal_priority or [],
        current_focus=current_focus or [],
        decision_style=decision_style,
        risk_profile=risk_profile,
        recurring_topics=recurring_topics or [],
        stable_biases=stable_biases or [],
        emotional_signals=emotional_signals or [],
        new_traits=new_traits or [],
        important_decisions=important_decisions or [],
        confidence_notes=confidence_notes or [],
        provider_name="local_fallback",
        metadata={"snapshot_scope": snapshot_scope},
        created_at=datetime.fromisoformat(f"{date_value}T12:00:00+00:00"),
    )
    markdown_path = config.daily_notes_dir / f"{snapshot_id}.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("# snapshot\n", encoding="utf-8")
    with get_connection(config.database_path) as connection:
        insert_daily_persona_snapshot(connection, snapshot, markdown_path, snapshot_scope)


def test_rebuild_persona_core_with_multiple_snapshots(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(
        config,
        "dps_1",
        "2024-03-21",
        goal_priority=["Build the persona cockpit"],
        current_focus=["Readable CLI output"],
        decision_style="structured and analytical",
        risk_profile="cautious and validation-oriented",
        recurring_topics=["persona", "cli"],
        stable_biases=["local-first preference", "bias toward verification and determinism"],
        new_traits=["cares about readable outputs"],
        confidence_notes=["heuristic snapshot"],
    )
    seed_daily_snapshot(
        config,
        "dps_2",
        "2024-03-22",
        goal_priority=["Build the persona cockpit"],
        current_focus=["Readable CLI output", "Deterministic behavior"],
        decision_style="structured and analytical",
        risk_profile="cautious and validation-oriented",
        recurring_topics=["persona", "determinism"],
        stable_biases=["local-first preference", "preference for simple, readable systems"],
        new_traits=["cares about readable outputs"],
        important_decisions=["Decision: keep the design simple."],
        confidence_notes=["heuristic snapshot"],
    )

    result = rebuild_persona_core(config)

    assert result.status == "created"
    assert result.persona_core is not None
    assert "local-first preference" in result.persona_core.stable_biases
    assert result.persona_core.decision_style == "structured and analytical"
    assert result.persona_core.risk_profile == "cautious and validation-oriented"
    assert result.persona_core.snapshot_scope == "all"
    assert result.persona_core.source_snapshot_ids == ["dps_1", "dps_2"]


def test_rebuild_persona_core_separates_stable_traits_from_recent_shifts(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(
        config,
        "dps_a",
        "2024-03-21",
        goal_priority=["Build the persona cockpit"],
        current_focus=["Readable CLI output"],
        recurring_topics=["persona"],
        stable_biases=["local-first preference"],
    )
    seed_daily_snapshot(
        config,
        "dps_b",
        "2024-03-22",
        goal_priority=["Build the persona cockpit"],
        current_focus=["Readable CLI output"],
        recurring_topics=["persona"],
        stable_biases=["local-first preference"],
        new_traits=["exploring agent memory playback"],
    )

    result = rebuild_persona_core(config)

    assert result.persona_core is not None
    assert "Build the persona cockpit" in result.persona_core.long_term_goals
    assert any("trait: exploring agent memory playback" == shift for shift in result.persona_core.recent_shifts)
    assert any("One-off goals" in note or "Recent shifts remain separate" in note for note in result.persona_core.confidence_notes)


def test_rebuild_persona_core_with_no_snapshots_returns_empty_result(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)

    result = rebuild_persona_core(config)

    assert result.status == "empty"
    assert result.persona_core is None


def test_rebuild_persona_core_is_deterministic_for_same_snapshots(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(
        config,
        "dps_det_1",
        "2024-03-21",
        goal_priority=["Build the persona cockpit"],
        current_focus=["Readable CLI output"],
        decision_style="structured and analytical",
        recurring_topics=["persona"],
        stable_biases=["local-first preference"],
    )
    seed_daily_snapshot(
        config,
        "dps_det_2",
        "2024-03-22",
        goal_priority=["Build the persona cockpit"],
        current_focus=["Readable CLI output"],
        decision_style="structured and analytical",
        recurring_topics=["persona"],
        stable_biases=["local-first preference"],
    )

    first = rebuild_persona_core(config)
    second = rebuild_persona_core(config)

    assert first.persona_core is not None
    assert second.persona_core is not None
    assert first.persona_core.model_dump() == second.persona_core.model_dump()


def test_rebuild_persona_core_supports_scope_filtering(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(
        config,
        "dps_all",
        "2024-03-21",
        goal_priority=["Build everything"],
        snapshot_scope="all",
        stable_biases=["local-first preference"],
    )
    seed_daily_snapshot(
        config,
        "dps_chat",
        "2024-03-21",
        goal_priority=["Import ChatGPT history"],
        snapshot_scope="source_type:chatgpt_export",
        stable_biases=["preference for simple, readable systems"],
    )

    result = rebuild_persona_core(config, snapshot_scope="source_type:chatgpt_export")

    assert result.persona_core is not None
    assert result.persona_core.snapshot_scope == "source_type:chatgpt_export"
    assert result.persona_core.source_snapshot_ids == ["dps_chat"]
    assert "Import ChatGPT history" in result.persona_core.long_term_goals


def test_persona_export_writes_json_and_markdown(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(
        config,
        "dps_export",
        "2024-03-21",
        goal_priority=["Build the persona cockpit"],
        stable_biases=["local-first preference"],
    )
    rebuild_persona_core(config)

    export_result = export_persona_core(config)

    assert export_result.status == "exported"
    assert export_result.json_path is not None
    assert export_result.markdown_path is not None
    json_payload = json.loads(export_result.json_path.read_text(encoding="utf-8"))
    markdown_payload = export_result.markdown_path.read_text(encoding="utf-8")
    assert json_payload["snapshot_scope"] == "all"
    assert "# Persona Core" in markdown_payload


def test_show_persona_core_returns_readable_summary(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(
        config,
        "dps_show",
        "2024-03-21",
        goal_priority=["Build the persona cockpit"],
        stable_biases=["local-first preference"],
        decision_style="structured and analytical",
    )
    rebuild_persona_core(config)

    result = show_persona_core(config)
    summary = format_persona_core_summary(result.persona_core)

    assert result.status == "loaded"
    assert "Persona Core" in summary
    assert "identity:" in summary
    assert "source_snapshot_ids:" in summary


def test_current_persona_core_is_stored_in_sqlite(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(
        config,
        "dps_store",
        "2024-03-21",
        goal_priority=["Build the persona cockpit"],
        stable_biases=["local-first preference"],
    )

    rebuild_persona_core(config)

    with get_connection(config.database_path) as connection:
        persona_core = get_current_persona_core(connection)

    assert persona_core is not None
    assert persona_core.snapshot_scope == "all"
    assert persona_core.source_snapshot_ids == ["dps_store"]
