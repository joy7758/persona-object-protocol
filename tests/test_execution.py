from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from typer.testing import CliRunner

from pop_cockpit import cli as cli_module
from pop_cockpit.config import AppConfig
from pop_cockpit.execution import (
    get_execution_detail,
    propose_execution_intent,
    reject_execution_intent,
    simulate_execution_intent,
)
from pop_cockpit.injector import ask_question
from pop_cockpit.persona import rebuild_persona_core
from pop_cockpit.schemas import (
    DailyPersonaSnapshot,
    DateRange,
    ExecutionIntent,
    ExecutionResult,
    ImportedRecord,
)
from pop_cockpit.storage import (
    ensure_runtime,
    get_connection,
    insert_daily_persona_snapshot,
    insert_imported_record,
    list_execution_intents,
    list_execution_results,
)
from pop_cockpit.webapp import create_app

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
    content: str,
    source_type: str = "text",
    imported_at: datetime | None = None,
) -> None:
    ensure_runtime(config)
    record = ImportedRecord(
        id=record_id,
        source_type=source_type,
        source_path=f"/tmp/{record_id}.txt",
        imported_at=imported_at or datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
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
        current_focus=["Readable execution layer"],
        decision_style="structured and analytical",
        risk_profile="cautious and validation-oriented",
        recurring_topics=["persona", "execution"],
        stable_biases=["local-first preference"],
        emotional_signals=["confidence"],
        new_traits=["prefers explicit safety boundaries"],
        important_decisions=["Decision: default to simulation first."],
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
    seed_daily_snapshot(config, "dps_exec")
    seed_imported_record(config, "imp_exec", content="POP should simulate software actions before real execution.")
    rebuild_persona_core(config)
    ask_result = ask_question(config, "What should POP execute next?", persist=True)
    assert ask_result.session is not None
    return ask_result.session.session_id


def test_execution_schemas_validate_expected_values() -> None:
    intent = ExecutionIntent(
        intent_id="exi_123",
        created_at=datetime(2026, 3, 22, 10, 0, tzinfo=UTC),
        action_type="write_summary",
        target_type="software_tool",
        target_name="daily_brief",
        parameters={"scope": "weekly"},
    )
    result = ExecutionResult(
        result_id="exr_123",
        intent_id="exi_123",
        created_at=datetime(2026, 3, 22, 10, 1, tzinfo=UTC),
        adapter_type="software_tool",
        execution_mode="simulation",
        success=True,
        output_text="Would call tool.",
    )

    assert intent.requires_confirmation is True
    assert intent.status == "proposed"
    assert result.execution_mode == "simulation"


def test_execution_schemas_reject_invalid_values() -> None:
    with pytest.raises(ValidationError):
        ExecutionIntent(
            intent_id="bad",
            created_at=datetime(2026, 3, 22, 10, 0, tzinfo=UTC),
            action_type="write_summary",
            target_type="not_real",
            target_name="daily_brief",
        )


def test_propose_and_simulate_execution_persists_results(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = create_saved_session(config)

    proposed = propose_execution_intent(
        config,
        source_session_id=session_id,
        action_type="write_summary",
        target_type="software_tool",
        target_name="daily_brief",
        parameters={"scope": "weekly"},
        rationale="Turn the saved session into a concise deliverable.",
    )

    assert proposed.status == "created"
    assert proposed.intent is not None
    assert proposed.intent.requires_confirmation is True
    assert proposed.intent.persona_core_version_id is not None
    assert proposed.intent.source_audit_id is not None
    assert proposed.intent_artifact_path is not None and proposed.intent_artifact_path.exists()

    simulated = simulate_execution_intent(config, proposed.intent.intent_id)

    assert simulated.status == "simulated"
    assert simulated.result is not None
    assert "Would call software tool" in simulated.result.output_text
    assert simulated.result_artifact_path is not None and simulated.result_artifact_path.exists()

    with get_connection(config.database_path) as connection:
        intents = list_execution_intents(connection)
        results = list_execution_results(connection)

    assert len(intents) == 1
    assert intents[0].status == "simulated"
    assert len(results) == 1
    assert results[0].intent_id == proposed.intent.intent_id


def test_duplicate_execution_intent_returns_existing(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = create_saved_session(config)

    first = propose_execution_intent(
        config,
        source_session_id=session_id,
        action_type="write_summary",
        target_type="software_tool",
        target_name="daily_brief",
        parameters={"scope": "weekly"},
        rationale="Turn the saved session into a concise deliverable.",
    )
    second = propose_execution_intent(
        config,
        source_session_id=session_id,
        action_type="write_summary",
        target_type="software_tool",
        target_name="daily_brief",
        parameters={"scope": "weekly"},
        rationale="Turn the saved session into a concise deliverable.",
    )

    assert first.intent is not None
    assert second.status == "existing"
    assert second.intent is not None
    assert second.intent.intent_id == first.intent.intent_id


def test_execution_page_renders_and_can_propose_intent(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = create_saved_session(config)
    client = TestClient(create_app(config))

    page = client.get("/execution")
    assert page.status_code == 200
    assert "动作草案" in page.text

    response = client.post(
        "/execution/propose",
        data={
            "source_session_id": session_id,
            "snapshot_scope": "all",
            "action_type": "write_summary",
            "target_type": "software_tool",
            "target_name": "daily_brief",
            "parameters_text": '{"scope":"weekly"}',
            "rationale": "Turn the saved session into a concise deliverable.",
            "safety_level": "medium",
            "requires_confirmation": "true",
        },
    )

    assert response.status_code == 200
    assert "已创建新的动作草案。" in response.text
    assert "daily_brief" in response.text
    assert "确认并预演" in response.text


def test_execution_endpoints_simulate_and_reject(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = create_saved_session(config)
    first = propose_execution_intent(
        config,
        source_session_id=session_id,
        action_type="write_summary",
        target_type="software_tool",
        target_name="daily_brief",
        parameters={"scope": "weekly"},
        rationale="Simulate a safe summary action.",
    )
    second = propose_execution_intent(
        config,
        source_session_id=session_id,
        action_type="sync_status",
        target_type="simulated_device",
        target_name="lobster_carrier",
        parameters={"command": "blink"},
        rationale="Keep device execution simulated only.",
    )
    assert first.intent is not None and second.intent is not None
    client = TestClient(create_app(config))

    simulate_response = client.post(f"/execution/{first.intent.intent_id}/simulate")
    reject_response = client.post(f"/execution/{second.intent.intent_id}/reject")

    assert simulate_response.status_code == 200
    assert "已在本地完成这条动作草案的预演。" in simulate_response.text
    assert reject_response.status_code == 200
    assert "已丢弃这条动作草案。" in reject_response.text


def test_execution_api_endpoints_return_expected_payload(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = create_saved_session(config)
    proposed = propose_execution_intent(
        config,
        source_session_id=session_id,
        action_type="write_summary",
        target_type="software_tool",
        target_name="daily_brief",
        parameters={"scope": "weekly"},
        rationale="Turn the saved session into a concise deliverable.",
    )
    assert proposed.intent is not None
    simulate_execution_intent(config, proposed.intent.intent_id)
    client = TestClient(create_app(config))

    list_response = client.get("/api/execution/list")
    detail_response = client.get(f"/api/execution/{proposed.intent.intent_id}")

    assert list_response.status_code == 200
    assert list_response.json()["intents"][0]["intent_id"] == proposed.intent.intent_id
    assert detail_response.status_code == 200
    assert detail_response.json()["intent"]["target_name"] == "daily_brief"
    assert detail_response.json()["results"][0]["execution_mode"] == "simulation"


def test_execution_cli_commands_are_usable(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    session_id = create_saved_session(config)
    proposed = propose_execution_intent(
        config,
        source_session_id=session_id,
        action_type="write_summary",
        target_type="software_tool",
        target_name="daily_brief",
        parameters={"scope": "weekly"},
        rationale="Turn the saved session into a concise deliverable.",
    )
    another = propose_execution_intent(
        config,
        source_session_id=session_id,
        action_type="sync_status",
        target_type="simulated_device",
        target_name="lobster_carrier",
        parameters={"command": "blink"},
        rationale="Keep device execution simulated only.",
    )
    assert proposed.intent is not None and another.intent is not None
    monkeypatch.setattr(cli_module, "_config", lambda: config)

    list_result = runner.invoke(cli_module.app, ["execution", "list"])
    show_result = runner.invoke(cli_module.app, ["execution", "show", proposed.intent.intent_id])
    simulate_result = runner.invoke(
        cli_module.app, ["execution", "simulate", proposed.intent.intent_id]
    )
    reject_result = runner.invoke(
        cli_module.app, ["execution", "reject", another.intent.intent_id]
    )

    assert list_result.exit_code == 0
    assert "daily_brief" in list_result.stdout
    assert show_result.exit_code == 0
    assert proposed.intent.intent_id in show_result.stdout
    assert simulate_result.exit_code == 0
    assert "processed through the simulator" in simulate_result.stdout
    assert reject_result.exit_code == 0
    assert "Rejected execution intent" in reject_result.stdout


def test_rejected_intent_still_records_failed_result(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    session_id = create_saved_session(config)
    proposed = propose_execution_intent(
        config,
        source_session_id=session_id,
        action_type="sync_status",
        target_type="simulated_device",
        target_name="lobster_carrier",
        parameters={"command": "blink"},
        rationale="Keep device execution simulated only.",
    )
    assert proposed.intent is not None

    reject_execution_intent(config, proposed.intent.intent_id)
    result = simulate_execution_intent(config, proposed.intent.intent_id)
    detail = get_execution_detail(config, proposed.intent.intent_id)

    assert result.status == "rejected"
    assert result.result is not None
    assert result.result.success is False
    assert detail.results[0].error_text == "Rejected intents cannot be executed."
