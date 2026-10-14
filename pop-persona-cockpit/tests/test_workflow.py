import json
from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from pop_cockpit import cli as cli_module
from pop_cockpit.config import AppConfig
from pop_cockpit.persona import show_persona_core
from pop_cockpit.settings import ProjectSettings, save_project_settings
from pop_cockpit.storage import ensure_runtime
from pop_cockpit.workflow import format_workflow_result, run_daily_workflow

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


def test_workflow_daily_orchestrates_import_extract_and_rebuild(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "note.txt").write_text(
        "Priority: finish the local-first persona cockpit.\n"
        "Current focus: readable CLI output and deterministic behavior.\n",
        encoding="utf-8",
    )
    save_project_settings(config, ProjectSettings(inbox_path=str(inbox)))

    result = run_daily_workflow(config)

    assert result.status == "completed"
    assert result.import_summary is not None
    assert result.import_summary.imported_count == 1
    assert result.extraction_result is not None
    assert result.extraction_result.status == "created"
    assert result.persona_result is not None
    assert result.persona_result.status == "created"
    assert result.artifact_path is not None and result.artifact_path.exists()
    assert result.log_path is not None and result.log_path.exists()
    today = date.today().isoformat()
    snapshot_json = config.daily_notes_dir / f"daily_snapshot_{today}_to_{today}.json"
    assert snapshot_json.exists()
    assert show_persona_core(config).persona_core is not None


def test_workflow_summary_output_is_readable(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "note.txt").write_text("Priority: build the cockpit.\n", encoding="utf-8")
    save_project_settings(config, ProjectSettings(inbox_path=str(inbox)))

    result = run_daily_workflow(config, command_name="run-now")
    summary = format_workflow_result(result)

    assert "imported:" in summary
    assert "daily_snapshot_status:" in summary
    assert "persona_rebuild_status:" in summary
    assert "rolling_log:" in summary


def test_workflow_run_now_cli_calls_same_logic(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "note.txt").write_text("Priority: build the cockpit.\n", encoding="utf-8")
    save_project_settings(config, ProjectSettings(inbox_path=str(inbox)))
    monkeypatch.setattr(cli_module, "_config", lambda: config)

    result = runner.invoke(cli_module.app, ["workflow", "run-now"])

    assert result.exit_code == 0
    assert "Workflow run-now completed" in result.stdout
    assert "imported:" in result.stdout


def test_workflow_run_record_is_written_as_json(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "note.txt").write_text("Priority: build the cockpit.\n", encoding="utf-8")
    save_project_settings(config, ProjectSettings(inbox_path=str(inbox)))

    result = run_daily_workflow(config)

    assert result.artifact_path is not None
    payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert payload["command_name"] == "daily"
    assert payload["imported_count"] == 1
    assert payload["daily_snapshot_status"] == "created"
