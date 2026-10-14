from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from pop_cockpit.config import AppConfig
from pop_cockpit.persona import rebuild_persona_core
from pop_cockpit.schemas import (
    DailyPersonaSnapshot,
    DateRange,
    ImportedRecord,
    ProjectSettings,
    SessionRecord,
)
from pop_cockpit.settings import load_project_settings, save_project_settings
from pop_cockpit.storage import (
    ensure_runtime,
    get_connection,
    get_current_persona_core,
    get_session_record,
    insert_daily_persona_snapshot,
    insert_imported_record,
    insert_session_record,
)
from pop_cockpit.sync import (
    ensure_device_identity,
    export_new_event_package,
    export_persona_sync_package,
    get_sync_status,
    import_remote_packages,
    initialize_sync,
    run_sync_now,
    set_sync_passphrase,
)
from pop_cockpit.webapp import create_app


def make_test_config(root: Path) -> AppConfig:
    data_dir = root / "data"
    return AppConfig(
        root_dir=root,
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


def seed_daily_snapshot(config: AppConfig, snapshot_id: str, *, date_value: str = "2026-03-22") -> None:
    ensure_runtime(config)
    snapshot = DailyPersonaSnapshot(
        id=snapshot_id,
        date_range=DateRange(date_from=date_value, date_to=date_value),
        source_record_ids=[f"imp_{snapshot_id}"],
        goal_priority=["Build POP Sync Helper Mini"],
        current_focus=["Safe local-first sync"],
        decision_style="structured and analytical",
        risk_profile="cautious and validation-oriented",
        recurring_topics=["persona", "sync"],
        stable_biases=["prefer recoverable packages"],
        emotional_signals=["confidence"],
        new_traits=["thinks in versioned artifacts"],
        important_decisions=["Do not sync the SQLite database file."],
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


def seed_persona(config: AppConfig) -> None:
    seed_imported_record(config, "imp_sync_persona", content="Keep sync local-first and recoverable.")
    seed_daily_snapshot(config, "dps_sync_persona")
    rebuild_persona_core(config)


def seed_session(
    config: AppConfig,
    session_id: str,
    *,
    feedback_status: str = "not_reviewed",
    feedback_note: str = "",
    feedback_updated_at: datetime | None = None,
) -> None:
    ensure_runtime(config)
    session = SessionRecord(
        session_id=session_id,
        question="How should POP sync safely?",
        snapshot_scope="all",
        persona_core_version_id=None,
        used_snapshot_ids=[],
        used_memory_ids=[],
        used_persona_fields=[],
        prompt_context="",
        response=None,
        mode="dry_run",
        retrieval_notes=[],
        source_type_filter=None,
        recent_days=7,
        artifact_path="",
        markdown_path="",
        feedback_status=feedback_status,
        feedback_note=feedback_note,
        feedback_updated_at=feedback_updated_at,
        created_at=datetime(2026, 3, 22, 12, 0, tzinfo=UTC),
    )
    with get_connection(config.database_path) as connection:
        insert_session_record(connection, session)


def init_sync_device(
    config: AppConfig,
    drive_root: Path,
    *,
    role: str,
    device_name: str,
    passphrase: str = "pop-sync-secret",
) -> None:
    ensure_runtime(config)
    save_project_settings(config, ProjectSettings())
    init_result = initialize_sync(
        config,
        root_path=str(drive_root),
        role=role,
        device_name=device_name,
    )
    assert init_result.status == "configured"
    passphrase_result = set_sync_passphrase(config, passphrase)
    assert passphrase_result.status == "saved"


def test_device_identity_initialization(tmp_path: Path) -> None:
    config = make_test_config(tmp_path / "identity")
    ensure_runtime(config)

    settings = ensure_device_identity(config)
    reloaded = load_project_settings(config)

    assert settings.device_id.startswith("dev_")
    assert settings.device_name
    assert reloaded.device_id == settings.device_id


def test_sync_init_saves_root_role_and_name(tmp_path: Path) -> None:
    config = make_test_config(tmp_path / "init")
    drive_root = tmp_path / "drive"

    result = initialize_sync(
        config,
        root_path=str(drive_root),
        role="primary",
        device_name="mac-mini",
    )
    settings = load_project_settings(config)

    assert result.status == "configured"
    assert settings.sync_root_path == str(drive_root)
    assert settings.device_role == "primary"
    assert settings.device_name == "mac-mini"


def test_encrypted_persona_package_write_and_read(tmp_path: Path) -> None:
    drive_root = tmp_path / "drive"
    primary = make_test_config(tmp_path / "primary")
    secondary = make_test_config(tmp_path / "secondary")
    seed_persona(primary)
    init_sync_device(primary, drive_root, role="primary", device_name="mac-mini")
    init_sync_device(secondary, drive_root, role="secondary", device_name="laptop")

    export_result = export_persona_sync_package(primary, force=True)
    assert export_result.status == "exported"
    enc_files = list((drive_root / "packages" / "persona" / "history").glob("*.enc"))
    assert enc_files
    assert b"Keep sync local-first and recoverable." not in enc_files[0].read_bytes()

    import_result = import_remote_packages(secondary)
    assert import_result.status == "completed"
    with get_connection(secondary.database_path) as connection:
        persona_core = get_current_persona_core(connection, snapshot_scope="all")
    assert persona_core is not None
    assert "recoverable packages" in " ".join(persona_core.stable_biases)


def test_receipts_make_remote_import_idempotent(tmp_path: Path) -> None:
    drive_root = tmp_path / "drive"
    primary = make_test_config(tmp_path / "primary")
    secondary = make_test_config(tmp_path / "secondary")
    seed_persona(primary)
    init_sync_device(primary, drive_root, role="primary", device_name="mac-mini")
    init_sync_device(secondary, drive_root, role="secondary", device_name="laptop")

    export_persona_sync_package(primary, force=True)
    first_import = import_remote_packages(secondary)
    second_import = import_remote_packages(secondary)

    assert first_import.status == "completed"
    assert second_import.status == "noop"
    secondary_settings = load_project_settings(secondary)
    receipt_files = list((drive_root / "receipts" / secondary_settings.device_id).glob("*.json"))
    assert len(receipt_files) == 1


def test_primary_secondary_role_behavior_for_persona_exports(tmp_path: Path) -> None:
    drive_root = tmp_path / "drive"
    primary = make_test_config(tmp_path / "primary")
    secondary = make_test_config(tmp_path / "secondary")
    seed_persona(primary)
    seed_persona(secondary)
    init_sync_device(primary, drive_root, role="primary", device_name="mac-mini")
    init_sync_device(secondary, drive_root, role="secondary", device_name="laptop")

    primary_result = export_persona_sync_package(primary, force=True)
    secondary_result = export_persona_sync_package(secondary, force=True)

    assert primary_result.status == "exported"
    assert secondary_result.status == "skipped"


def test_sync_status_summary_includes_counts(tmp_path: Path) -> None:
    drive_root = tmp_path / "drive"
    config = make_test_config(tmp_path / "status")
    init_sync_device(config, drive_root, role="secondary", device_name="laptop")
    seed_session(
        config,
        "sess_pending",
        feedback_status="accepted",
        feedback_note="Looks right.",
        feedback_updated_at=datetime(2026, 3, 22, 13, 0, tzinfo=UTC),
    )

    summary = get_sync_status(config)

    assert summary.enabled is True
    assert summary.device_role == "secondary"
    assert summary.sync_root_path == str(drive_root)
    assert summary.pending_outgoing_count == 1
    assert summary.pending_incoming_count == 0


def test_conflict_file_is_created_for_missing_remote_target(tmp_path: Path) -> None:
    drive_root = tmp_path / "drive"
    primary = make_test_config(tmp_path / "primary")
    secondary = make_test_config(tmp_path / "secondary")
    init_sync_device(primary, drive_root, role="primary", device_name="mac-mini")
    init_sync_device(secondary, drive_root, role="secondary", device_name="laptop")
    seed_session(
        primary,
        "sess_shared",
        feedback_status="accepted",
        feedback_note="Ship this direction.",
        feedback_updated_at=datetime(2026, 3, 22, 14, 0, tzinfo=UTC),
    )

    export_result = export_new_event_package(primary)
    import_result = import_remote_packages(secondary)

    assert export_result.status == "exported"
    assert import_result.status == "completed"
    conflict_files = list((drive_root / "conflicts").glob("*.json"))
    assert len(conflict_files) == 1
    assert "missing_session" in conflict_files[0].read_text(encoding="utf-8")


def test_sync_page_renders(tmp_path: Path) -> None:
    config = make_test_config(tmp_path / "web")
    ensure_runtime(config)
    client = TestClient(create_app(config))

    response = client.get("/sync")

    assert response.status_code == 200
    assert "Sync Now" in response.text
    assert "最近同步历史" in response.text
    assert "Import Remote Updates" in response.text


def test_sync_now_workflow_imports_primary_persona_on_secondary(tmp_path: Path) -> None:
    drive_root = tmp_path / "drive"
    primary = make_test_config(tmp_path / "primary")
    secondary = make_test_config(tmp_path / "secondary")
    seed_persona(primary)
    init_sync_device(primary, drive_root, role="primary", device_name="mac-mini")
    init_sync_device(secondary, drive_root, role="secondary", device_name="laptop")

    primary_result = run_sync_now(primary)
    before_import = get_sync_status(secondary)
    secondary_result = run_sync_now(secondary)

    assert primary_result.status == "completed"
    assert before_import.pending_incoming_count == 1
    assert secondary_result.status == "completed"
    with get_connection(secondary.database_path) as connection:
        persona_core = get_current_persona_core(connection, snapshot_scope="all")
        imported_session = get_session_record(connection, "sess_shared")
    assert persona_core is not None
    assert persona_core.identity is not None
    assert imported_session is None
