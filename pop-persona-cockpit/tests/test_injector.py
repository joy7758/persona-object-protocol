import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from pop_cockpit.config import AppConfig
from pop_cockpit.injector import ask_question, retrieve_relevant_memories
from pop_cockpit.persona import rebuild_persona_core
from pop_cockpit.schemas import DailyPersonaSnapshot, DateRange, ImportedRecord
from pop_cockpit.storage import (
    ensure_runtime,
    get_connection,
    insert_daily_persona_snapshot,
    insert_imported_record,
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


def seed_imported_record(
    config: AppConfig,
    record_id: str,
    *,
    source_type: str,
    content: str,
    imported_at: datetime,
    metadata: dict | None = None,
    tags: list[str] | None = None,
) -> None:
    ensure_runtime(config)
    record = ImportedRecord(
        id=record_id,
        source_type=source_type,
        source_path=f"/tmp/{record_id}.{source_type}",
        imported_at=imported_at,
        content=content,
        content_hash=f"hash-{record_id}",
        tags=tags or [],
        metadata=metadata or {},
    )
    with get_connection(config.database_path) as connection:
        insert_imported_record(connection, record)


def seed_daily_snapshot(
    config: AppConfig,
    snapshot_id: str,
    *,
    date_value: str,
    snapshot_scope: str,
    goal_priority: list[str],
    current_focus: list[str],
    stable_biases: list[str],
    recurring_topics: list[str],
    decision_style: str = "structured and analytical",
    risk_profile: str = "cautious and validation-oriented",
    recent_traits: list[str] | None = None,
) -> None:
    ensure_runtime(config)
    snapshot = DailyPersonaSnapshot(
        id=snapshot_id,
        date_range=DateRange(date_from=date_value, date_to=date_value),
        source_record_ids=[f"imp_{snapshot_id}"],
        goal_priority=goal_priority,
        current_focus=current_focus,
        decision_style=decision_style,
        risk_profile=risk_profile,
        recurring_topics=recurring_topics,
        stable_biases=stable_biases,
        emotional_signals=["confidence"],
        new_traits=recent_traits or [],
        important_decisions=["Decision: keep the design simple."],
        confidence_notes=["heuristic snapshot"],
        provider_name="local_fallback",
        metadata={"snapshot_scope": snapshot_scope},
        created_at=datetime.fromisoformat(f"{date_value}T12:00:00+00:00"),
    )
    markdown_path = config.daily_notes_dir / f"{snapshot_id}.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("# snapshot\n", encoding="utf-8")
    with get_connection(config.database_path) as connection:
        insert_daily_persona_snapshot(connection, snapshot, markdown_path, snapshot_scope)


def session_rows(database_path: Path) -> list[tuple]:
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
            """
            SELECT session_id, snapshot_scope, persona_core_version_id, used_memory_ids_json, mode
            FROM sessions
            ORDER BY created_at ASC, session_id ASC
            """
        ).fetchall()


def test_ask_with_existing_persona_core_and_memory(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(
        config,
        "dps_ask",
        date_value="2024-03-21",
        snapshot_scope="all",
        goal_priority=["Build the persona cockpit"],
        current_focus=["Readable CLI output"],
        stable_biases=["local-first preference", "preference for simple, readable systems"],
        recurring_topics=["persona", "cli"],
        recent_traits=["exploring agent memory playback"],
    )
    rebuild_persona_core(config)
    seed_imported_record(
        config,
        "imp_memory_1",
        source_type="text",
        content="We should keep the CLI readable and deterministic for the persona cockpit.",
        imported_at=datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
        tags=["cli", "persona"],
    )

    result = ask_question(config, "How should I evolve the persona cockpit CLI?", dry_run=True)

    assert result.status == "created"
    assert result.session is not None
    assert result.session.mode == "dry_run"
    assert result.session.used_memory_ids == ["imp_memory_1"]
    assert "## Persona Core Summary" in result.prompt_package
    assert "## Relevant Memory Excerpts" in result.prompt_package
    assert "How should I evolve the persona cockpit CLI?" in result.prompt_package


def test_ask_with_no_persona_core_available_returns_readable_message(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)

    result = ask_question(config, "What matters today?")

    assert result.status == "empty"
    assert result.session is None
    assert "No persona core found" in result.message


def test_retrieval_ordering_is_deterministic(tmp_path: Path) -> None:
    record_a = ImportedRecord(
        id="imp_a",
        source_type="text",
        source_path="/tmp/a.txt",
        imported_at=datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
        content="persona cockpit cli memory",
        content_hash="hash-a",
        tags=["persona"],
        metadata={},
    )
    record_b = ImportedRecord(
        id="imp_b",
        source_type="text",
        source_path="/tmp/b.txt",
        imported_at=datetime(2026, 3, 22, 10, 0, tzinfo=UTC),
        content="persona cockpit cli memory",
        content_hash="hash-b",
        tags=["persona"],
        metadata={},
    )

    first = retrieve_relevant_memories("persona cockpit cli", [record_a, record_b], limit=2)
    second = retrieve_relevant_memories("persona cockpit cli", [record_a, record_b], limit=2)

    assert [match.record.id for match in first] == ["imp_b", "imp_a"]
    assert [match.record.id for match in first] == [match.record.id for match in second]


def test_dry_run_writes_session_json(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(
        config,
        "dps_json",
        date_value="2024-03-21",
        snapshot_scope="all",
        goal_priority=["Build the persona cockpit"],
        current_focus=["Readable CLI output"],
        stable_biases=["local-first preference"],
        recurring_topics=["persona"],
    )
    rebuild_persona_core(config)
    seed_imported_record(
        config,
        "imp_json",
        source_type="text",
        content="Readable CLI output helps the persona cockpit.",
        imported_at=datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
    )

    result = ask_question(config, "How do I improve readable CLI output?", dry_run=True)

    assert result.json_path is not None
    payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert payload["session_id"] == result.session.session_id
    assert payload["used_memory_ids"] == ["imp_json"]
    assert "Persona-Assisted Prompt Package" in payload["prompt_context"]


def test_ask_persists_session_in_sqlite(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(
        config,
        "dps_sql",
        date_value="2024-03-21",
        snapshot_scope="all",
        goal_priority=["Build the persona cockpit"],
        current_focus=["Readable CLI output"],
        stable_biases=["local-first preference"],
        recurring_topics=["persona"],
    )
    rebuild_persona_core(config)
    seed_imported_record(
        config,
        "imp_sql",
        source_type="text",
        content="Persona cockpit memory for sqlite session persistence.",
        imported_at=datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
    )

    result = ask_question(config, "What should I remember about persona cockpit memory?", dry_run=True)

    rows = session_rows(config.database_path)
    assert len(rows) == 1
    assert rows[0][0] == result.session.session_id
    assert rows[0][1] == "all"
    assert json.loads(rows[0][3]) == ["imp_sql"]
    assert rows[0][4] == "dry_run"


def test_ask_is_scope_aware(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(
        config,
        "dps_all",
        date_value="2024-03-21",
        snapshot_scope="all",
        goal_priority=["Build everything"],
        current_focus=["General system work"],
        stable_biases=["local-first preference"],
        recurring_topics=["system"],
    )
    seed_daily_snapshot(
        config,
        "dps_chat",
        date_value="2024-03-21",
        snapshot_scope="source_type:chatgpt_export",
        goal_priority=["Import ChatGPT history"],
        current_focus=["Conversation memory"],
        stable_biases=["preference for simple, readable systems"],
        recurring_topics=["chatgpt", "memory"],
    )
    rebuild_persona_core(config)
    rebuild_persona_core(config, snapshot_scope="source_type:chatgpt_export")
    seed_imported_record(
        config,
        "imp_chat_scope",
        source_type="chatgpt_export",
        content="ChatGPT conversation memory about preserving message roles.",
        imported_at=datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
        metadata={"created_at": "2024-03-21T06:03:21+00:00"},
    )

    result = ask_question(
        config,
        "How should I preserve ChatGPT conversation memory?",
        snapshot_scope="source_type:chatgpt_export",
        dry_run=True,
    )

    assert result.session is not None
    assert result.session.snapshot_scope == "source_type:chatgpt_export"
    assert result.session.used_snapshot_ids == ["dps_chat"]
    assert result.session.persona_core_version_id is not None


def test_ask_supports_source_type_filtering(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(
        config,
        "dps_filter",
        date_value="2024-03-21",
        snapshot_scope="all",
        goal_priority=["Build the persona cockpit"],
        current_focus=["Readable CLI output"],
        stable_biases=["local-first preference"],
        recurring_topics=["persona"],
    )
    rebuild_persona_core(config)
    seed_imported_record(
        config,
        "imp_text",
        source_type="text",
        content="Persona cockpit memory from plain text.",
        imported_at=datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
    )
    seed_imported_record(
        config,
        "imp_chatgpt",
        source_type="chatgpt_export",
        content="Persona cockpit memory from ChatGPT export.",
        imported_at=datetime(2026, 3, 22, 9, 1, tzinfo=UTC),
    )

    result = ask_question(
        config,
        "What matters for the persona cockpit memory?",
        source_type="chatgpt_export",
        dry_run=True,
    )

    assert result.session is not None
    assert result.session.used_memory_ids == ["imp_chatgpt"]
    assert result.session.source_type_filter == "chatgpt_export"
