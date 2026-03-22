import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from pop_cockpit.browser_capture import reset_capture_diagnostics
from pop_cockpit.config import AppConfig
from pop_cockpit.persona import rebuild_persona_core
from pop_cockpit.scheduler import SchedulerResult
from pop_cockpit.schemas import DailyPersonaSnapshot, DateRange, ImportedRecord
from pop_cockpit.storage import (
    ensure_runtime,
    get_connection,
    insert_daily_persona_snapshot,
    insert_imported_record,
)
from pop_cockpit.webapp import create_app


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


def setup_function() -> None:
    reset_capture_diagnostics()


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
        current_focus=["Readable CLI output"],
        decision_style="structured and analytical",
        risk_profile="cautious and validation-oriented",
        recurring_topics=["persona", "cli"],
        stable_biases=["local-first preference"],
        emotional_signals=["confidence"],
        new_traits=["prefers readable systems"],
        important_decisions=["Decision: keep the design simple."],
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


def session_count(database_path: Path) -> int:
    with sqlite3.connect(database_path) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])


def build_client(config: AppConfig, monkeypatch) -> TestClient:
    monkeypatch.setattr(
        "pop_cockpit.web_services.scheduler_status",
        lambda _config: SchedulerResult(
            status="installed",
            message="stubbed",
            scheduled_time="22:30",
            inbox_path="~/pop-persona-cockpit-inbox",
            installed=True,
            enabled=False,
        ),
    )
    return TestClient(create_app(config))


def test_dashboard_page_renders(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    client = build_client(config, monkeypatch)

    response = client.get("/")

    assert response.status_code == 200
    assert "立即更新我的画像" in response.text
    assert "打开我的数字人格" in response.text
    assert "浏览器自动记录" in response.text
    assert "测试采集" in response.text


def test_import_page_accepts_uploaded_text_file(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    client = build_client(config, monkeypatch)

    response = client.post(
        "/imports/files",
        files=[("files", ("note.txt", b"Priority: build the cockpit.\n", "text/plain"))],
    )

    assert response.status_code == 200
    assert "已导入 1 个文件到 POP。" in response.text
    assert "Priority: build the cockpit." in response.text


def test_persona_page_rebuild_action_renders_current_core(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(config, "dps_web")
    client = build_client(config, monkeypatch)

    response = client.post("/persona/rebuild", data={"scope": "all"})

    assert response.status_code == 200
    assert "已更新「全部」这组视图的人格画像。" in response.text
    assert "我当前的数字人格" in response.text


def test_ask_page_assemble_context_only_does_not_persist_session(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(config, "dps_ask")
    rebuild_persona_core(config)
    seed_imported_record(config, "imp_web_ask", content="Persona cockpit CLI memory.")
    client = build_client(config, monkeypatch)

    response = client.post(
        "/ask",
        data={
            "question": "How should I evolve the persona cockpit CLI?",
            "scope": "all",
            "days": "7",
            "source_type": "",
            "action": "assemble",
        },
    )

    assert response.status_code == 200
    assert "已整理好上下文，但还没有保存成新的分析记录。" in response.text
    assert "Persona-Assisted Prompt Package" in response.text
    assert session_count(config.database_path) == 0


def test_ask_page_save_session_persists_and_audit_page_renders(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(config, "dps_save")
    rebuild_persona_core(config)
    seed_imported_record(config, "imp_web_save", content="Persona cockpit memory for saved session.")
    client = build_client(config, monkeypatch)

    ask_response = client.post(
        "/ask",
        data={
            "question": "What should POP remember?",
            "scope": "all",
            "days": "7",
            "source_type": "",
            "action": "save",
        },
    )

    assert ask_response.status_code == 200
    assert "已保存分析：" in ask_response.text
    assert session_count(config.database_path) == 1

    audit_response = client.get("/audit")

    assert audit_response.status_code == 200
    assert "为什么 POP 会这样分析" in audit_response.text
    assert "What should POP remember?" in audit_response.text


def test_settings_page_scheduler_install_action_is_rendered(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    monkeypatch.setattr(
        "pop_cockpit.webapp.install_scheduler_from_web",
        lambda _config, inbox_path, hour, minute: SchedulerResult(
            status="installed",
            message=f"已为 {inbox_path} 安装 {hour:02d}:{minute:02d} 的自动更新。",
            scheduled_time=f"{hour:02d}:{minute:02d}",
            inbox_path=inbox_path,
            installed=True,
            enabled=False,
        ),
    )
    client = build_client(config, monkeypatch)

    response = client.post(
        "/settings/scheduler/install",
        data={"inbox_path": "~/pop-persona-cockpit-inbox", "hour": "22", "minute": "30"},
    )

    assert response.status_code == 200
    assert "已为 ~/pop-persona-cockpit-inbox 安装 22:30 的自动更新。" in response.text
    assert "自动更新状态" in response.text


def test_dashboard_capture_test_action_is_rendered(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    client = build_client(config, monkeypatch)

    response = client.post("/dashboard/test-capture")

    assert response.status_code == 200
    assert "测试采集成功" in response.text
    assert "浏览器自动记录" in response.text
