import zipfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from pop_cockpit import cli as cli_module
from pop_cockpit.config import AppConfig
from pop_cockpit.execution import propose_execution_intent, review_execution_intent
from pop_cockpit.injector import ask_question
from pop_cockpit.persona import rebuild_persona_core
from pop_cockpit.schemas import DailyPersonaSnapshot, DateRange, ImportedRecord, ProjectSettings
from pop_cockpit.settings import save_project_settings
from pop_cockpit.storage import (
    ensure_runtime,
    get_connection,
    get_session_record,
    insert_daily_persona_snapshot,
    insert_imported_record,
)
from pop_cockpit.webapp import create_app
from pop_cockpit.workflow import run_daily_workflow

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


def seed_imported_record(config: AppConfig, record_id: str, *, content: str) -> None:
    ensure_runtime(config)
    record = ImportedRecord(
        id=record_id,
        source_type="text",
        source_path=f"/tmp/{record_id}.txt",
        imported_at=datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
        content=content,
        content_hash=f"hash-{record_id}",
        tags=["persona"],
        metadata={},
    )
    with get_connection(config.database_path) as connection:
        insert_imported_record(connection, record)


def seed_daily_snapshot(config: AppConfig, snapshot_id: str, date_value: str = "2024-03-21") -> None:
    ensure_runtime(config)
    snapshot = DailyPersonaSnapshot(
        id=snapshot_id,
        date_range=DateRange(date_from=date_value, date_to=date_value),
        source_record_ids=[f"imp_{snapshot_id}"],
        goal_priority=["Build the persona cockpit"],
        current_focus=["Readable daily workflow"],
        decision_style="structured and analytical",
        risk_profile="cautious and validation-oriented",
        recurring_topics=["persona", "workflow"],
        stable_biases=["local-first preference"],
        emotional_signals=["confidence"],
        new_traits=["prefers human-readable daily routines"],
        important_decisions=["Decision: keep the automation simple."],
        confidence_notes=["heuristic snapshot"],
        provider_name="local_fallback",
        metadata={"snapshot_scope": "all"},
        created_at=datetime.fromisoformat(f"{date_value}T12:00:00+00:00"),
    )
    markdown_path = config.daily_notes_dir / f"{snapshot_id}.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("# snapshot\n", encoding="utf-8")
    with get_connection(config.database_path) as connection:
        insert_daily_persona_snapshot(connection, snapshot, markdown_path, "all")


def create_saved_session(config: AppConfig) -> str:
    seed_daily_snapshot(config, "dps_product")
    seed_imported_record(config, "imp_product", content="POP should feel simpler every day.")
    rebuild_persona_core(config)
    ask_result = ask_question(config, "How do I make POP simpler to use?", persist=True)
    assert ask_result.session is not None
    return ask_result.session.session_id


def test_session_feedback_is_persisted_from_web(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = create_saved_session(config)
    client = TestClient(create_app(config))

    response = client.post(
        f"/ask/{session_id}/feedback",
        data={"feedback_status": "accepted", "feedback_note": "This felt more natural."},
    )

    assert response.status_code == 200
    assert "已保存你对这次分析的反馈。" in response.text
    with get_connection(config.database_path) as connection:
        session = get_session_record(connection, session_id)
    assert session is not None
    assert session.feedback_status == "accepted"
    assert session.feedback_note == "This felt more natural."
    assert session.feedback_updated_at is not None


def test_execution_review_is_persisted(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = create_saved_session(config)
    proposed = propose_execution_intent(
        config,
        source_session_id=session_id,
        action_type="write_summary",
        target_type="software_tool",
        target_name="daily_brief",
        parameters={"scope": "daily"},
        rationale="Turn the saved analysis into a quick daily brief.",
    )
    assert proposed.intent is not None

    result = review_execution_intent(
        config,
        proposed.intent.intent_id,
        review_status="useful",
        review_note="This is the right level of action detail.",
    )

    assert result.status == "reviewed"
    assert result.intent is not None
    assert result.intent.review_status == "useful"
    assert result.intent.review_note == "This is the right level of action detail."


def test_dashboard_shows_product_summaries(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = create_saved_session(config)
    client = TestClient(create_app(config))
    client.post(
        f"/ask/{session_id}/feedback",
        data={"feedback_status": "accepted", "feedback_note": "Good summary."},
    )
    proposed = propose_execution_intent(
        config,
        source_session_id=session_id,
        action_type="write_summary",
        target_type="software_tool",
        target_name="daily_brief",
        parameters={"scope": "daily"},
        rationale="Turn the saved analysis into a quick daily brief.",
    )
    assert proposed.intent is not None
    review_execution_intent(
        config,
        proposed.intent.intent_id,
        review_status="useful",
        review_note="Helpful draft.",
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "最近分析" in response.text
    assert "最近动作草案" in response.text
    assert "采纳：" in response.text


def test_archive_after_import_moves_processed_and_failed_files(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    inbox = tmp_path / "inbox"
    archive = tmp_path / "archive"
    failed = tmp_path / "failed"
    inbox.mkdir()
    (inbox / "note.txt").write_text("Priority: keep POP tidy.\n", encoding="utf-8")
    (inbox / "ignore.png").write_bytes(b"png")
    save_project_settings(
        config,
        ProjectSettings(
            inbox_path=str(inbox),
            archive_path=str(archive),
            failed_path=str(failed),
            archive_after_import=True,
        ),
    )

    result = run_daily_workflow(config)

    workflow_date = result.run_record.workflow_date if result.run_record is not None else ""
    assert result.archived_count == 1
    assert result.failed_moved_count == 1
    assert not (inbox / "note.txt").exists()
    assert not (inbox / "ignore.png").exists()
    assert (archive / workflow_date / "note.txt").exists()
    assert (failed / workflow_date / "ignore.png").exists()


def test_persona_package_export_route_returns_zip(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    create_saved_session(config)
    client = TestClient(create_app(config))

    response = client.get("/persona/export/package?scope=all")

    assert response.status_code == 200
    package_path = config.persona_core_dir / "persona_package.zip"
    package_path.write_bytes(response.content)
    with zipfile.ZipFile(package_path) as archive:
        names = set(archive.namelist())
    assert "manifest.json" in names
    assert "persona_core.json" in names
    assert "recent_sessions.json" in names


def test_start_open_and_status_helpers_are_usable(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    save_project_settings(
        config,
        ProjectSettings(
            inbox_path=str(tmp_path / "inbox"),
            archive_path=str(tmp_path / "archive"),
            archive_after_import=True,
            auto_open_browser=True,
        ),
    )
    monkeypatch.setattr(cli_module, "_config", lambda: config)
    monkeypatch.setattr(
        "pop_cockpit.cli.run_pop_service",
        lambda _config, auto_open_browser: None,
    )
    monkeypatch.setattr(
        "pop_cockpit.cli.open_local_browser",
        lambda url: True,
    )
    monkeypatch.setattr(
        "pop_cockpit.cli.autostart_status",
        lambda _config: type(
            "AutostartStub",
            (),
            {"enabled": False},
        )(),
    )

    start_result = runner.invoke(cli_module.app, ["start"])
    open_result = runner.invoke(cli_module.app, ["open"])
    status_result = runner.invoke(cli_module.app, ["status"])

    assert start_result.exit_code == 0
    assert "POP is running at http://127.0.0.1:8765" in start_result.stdout
    assert "Browser auto-open: on" in start_result.stdout
    assert open_result.exit_code == 0
    assert "Opened http://127.0.0.1:8765" in open_result.stdout
    assert status_result.exit_code == 0
    assert "autostart: off" in status_result.stdout
    assert "automatic_updates:" in status_result.stdout
    assert "archive_after_import: yes" in status_result.stdout
