import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from pop_cockpit import cli as cli_module
from pop_cockpit.audit import build_audit_record, ensure_audit_record
from pop_cockpit.config import AppConfig
from pop_cockpit.injector import ask_question
from pop_cockpit.persona import rebuild_persona_core
from pop_cockpit.schemas import DailyPersonaSnapshot, DateRange, ImportedRecord
from pop_cockpit.storage import (
    ensure_runtime,
    get_audit_record,
    get_connection,
    get_session_record,
    insert_daily_persona_snapshot,
    insert_imported_record,
)

runner = CliRunner()


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
) -> None:
    ensure_runtime(config)
    snapshot = DailyPersonaSnapshot(
        id=snapshot_id,
        date_range=DateRange(date_from=date_value, date_to=date_value),
        source_record_ids=[f"imp_{snapshot_id}"],
        goal_priority=goal_priority,
        current_focus=current_focus,
        decision_style="structured and analytical",
        risk_profile="cautious and validation-oriented",
        recurring_topics=recurring_topics,
        stable_biases=stable_biases,
        emotional_signals=["confidence"],
        new_traits=["prefers readable systems"],
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


def seed_ready_session(config: AppConfig) -> str:
    seed_daily_snapshot(
        config,
        "dps_audit",
        date_value="2024-03-21",
        snapshot_scope="all",
        goal_priority=["Build the persona cockpit"],
        current_focus=["Readable CLI output"],
        stable_biases=["local-first preference"],
        recurring_topics=["persona", "audit"],
    )
    rebuild_persona_core(config)
    seed_imported_record(
        config,
        "imp_audit",
        source_type="text",
        content="Persona cockpit audit trail should stay readable and deterministic.",
        imported_at=datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
        tags=["persona", "audit"],
    )
    result = ask_question(config, "How do I review persona cockpit changes later?", dry_run=True)
    assert result.session is not None
    return result.session.session_id


def test_ask_creates_audit_artifact_for_dry_run_session(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = seed_ready_session(config)

    with get_connection(config.database_path) as connection:
        audit_record = get_audit_record(connection, session_id)

    assert audit_record is not None
    assert audit_record.session_id == session_id
    assert audit_record.mode == "dry_run"
    assert audit_record.response_present is False
    assert audit_record.response_hash is None


def test_audit_json_and_markdown_are_written(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = seed_ready_session(config)

    with get_connection(config.database_path) as connection:
        audit_record = get_audit_record(connection, session_id)

    assert audit_record is not None
    payload = json.loads(Path(audit_record.artifact_path).read_text(encoding="utf-8"))
    markdown = Path(audit_record.markdown_path).read_text(encoding="utf-8")
    assert payload["session_id"] == session_id
    assert payload["prompt_context_hash"] == audit_record.prompt_context_hash
    assert "# Session Audit" in markdown
    assert "Prompt Context Hash" in markdown


def test_audit_hash_generation_is_stable_for_same_session(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = seed_ready_session(config)

    with get_connection(config.database_path) as connection:
        session = get_session_record(connection, session_id)

    assert session is not None
    first = build_audit_record(config, session)
    second = build_audit_record(config, session)

    assert first.prompt_context_hash == second.prompt_context_hash
    assert first.response_hash == second.response_hash


def test_ensure_audit_avoids_duplicate_rows(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = seed_ready_session(config)

    result = ensure_audit_record(config, session_id)

    with sqlite3.connect(config.database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM audit_logs WHERE session_id = ?", (session_id,)).fetchone()[0]

    assert result.status == "existing"
    assert count == 1


def test_audit_list_command_outputs_recent_summaries(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    session_id = seed_ready_session(config)
    monkeypatch.setattr(cli_module, "_config", lambda: config)

    result = runner.invoke(cli_module.app, ["audit", "list", "--limit", "5"])

    assert result.exit_code == 0
    assert session_id in result.stdout
    assert "dry_run" in result.stdout
    assert "response" in result.stdout


def test_audit_show_command_outputs_full_details(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    session_id = seed_ready_session(config)
    monkeypatch.setattr(cli_module, "_config", lambda: config)

    result = runner.invoke(cli_module.app, ["audit", "show", session_id])

    assert result.exit_code == 0
    assert "Audit Record" in result.stdout
    assert session_id in result.stdout
    assert "Prompt Context Hash" in result.stdout
    assert "imp_audit" in result.stdout
