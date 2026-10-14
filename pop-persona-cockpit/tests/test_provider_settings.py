from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from pop_cockpit.config import AppConfig
from pop_cockpit.extractor import extract_daily_snapshot
from pop_cockpit.injector import ask_question
from pop_cockpit.llm_api import ProviderConnectionResult, ProviderError, mask_api_key
from pop_cockpit.persona import rebuild_persona_core
from pop_cockpit.schemas import DailyPersonaSnapshot, DateRange, ImportedRecord, ProjectSettings
from pop_cockpit.settings import load_project_settings, save_project_settings
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


def seed_daily_snapshot(config: AppConfig, snapshot_id: str) -> None:
    ensure_runtime(config)
    snapshot = DailyPersonaSnapshot(
        id=snapshot_id,
        date_range=DateRange(date_from="2024-03-21", date_to="2024-03-21"),
        source_record_ids=[f"imp_{snapshot_id}"],
        goal_priority=["Build POP"],
        current_focus=["Provider settings"],
        decision_style="structured and analytical",
        risk_profile="cautious and validation-oriented",
        recurring_topics=["persona", "api"],
        stable_biases=["local-first preference"],
        emotional_signals=["confidence"],
        new_traits=["prefers explicit configuration"],
        important_decisions=["Decision: keep API mode optional."],
        confidence_notes=["heuristic snapshot"],
        provider_name="local_fallback",
        metadata={"snapshot_scope": "all"},
        created_at=datetime(2024, 3, 21, 12, 0, tzinfo=UTC),
    )
    markdown_path = config.daily_notes_dir / f"{snapshot_id}.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("# snapshot\n", encoding="utf-8")
    with get_connection(config.database_path) as connection:
        insert_daily_persona_snapshot(connection, snapshot, markdown_path, "all")


def test_provider_settings_can_be_saved_from_web(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    client = TestClient(create_app(config))

    response = client.post(
        "/settings/provider/save",
        data={
            "provider_mode": "api",
            "api_base_url": "https://api.example.com/v1",
            "api_key": "sk-test-12345678",
            "default_model": "gpt-4.1",
            "extract_model": "gpt-4.1-mini",
            "persona_model": "gpt-4.1",
            "ask_model": "gpt-4.1",
            "fallback_to_local_on_error": "true",
        },
    )

    assert response.status_code == 200
    assert "已保存 AI 接口设置。" in response.text
    settings = load_project_settings(config)
    assert settings.provider_mode == "api"
    assert settings.api_base_url == "https://api.example.com/v1"
    assert settings.api_key == "sk-test-12345678"
    assert settings.default_model == "gpt-4.1"
    assert settings.fallback_to_local_on_error is True


def test_settings_page_masks_saved_api_key(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    save_project_settings(
        config,
        ProjectSettings(
            provider_mode="api",
            api_base_url="https://api.example.com/v1",
            api_key="sk-test-12345678",
            default_model="gpt-4.1",
        ),
    )
    client = TestClient(create_app(config))

    response = client.get("/settings")

    assert response.status_code == 200
    assert "AI 接口设置" in response.text
    assert "sk-test-12345678" not in response.text
    assert mask_api_key("sk-test-12345678") in response.text


def test_provider_test_action_handles_success_and_failure(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    client = TestClient(create_app(config))

    monkeypatch.setattr(
        "pop_cockpit.web_services.test_provider_connection",
        lambda settings: ProviderConnectionResult(
            success=True,
            checked_at=datetime(2026, 3, 22, 10, 0, tzinfo=UTC),
            message="连接成功，模型返回：POP connection ok.",
        ),
    )
    success_response = client.post(
        "/settings/provider/test",
        data={
            "provider_mode": "api",
            "api_base_url": "https://api.example.com/v1",
            "api_key": "sk-test-12345678",
            "default_model": "gpt-4.1",
            "extract_model": "",
            "persona_model": "",
            "ask_model": "gpt-4.1",
            "fallback_to_local_on_error": "true",
        },
    )
    assert success_response.status_code == 200
    assert "连接成功" in success_response.text

    def raise_failure(_settings):
        raise ProviderError("无法连接到 AI 接口：connection refused")

    monkeypatch.setattr("pop_cockpit.web_services.test_provider_connection", raise_failure)
    failure_response = client.post(
        "/settings/provider/test",
        data={
            "provider_mode": "api",
            "api_base_url": "https://api.example.com/v1",
            "api_key": "sk-test-12345678",
            "default_model": "gpt-4.1",
            "extract_model": "",
            "persona_model": "",
            "ask_model": "gpt-4.1",
            "fallback_to_local_on_error": "true",
        },
    )
    assert failure_response.status_code == 200
    assert "连接测试失败" in failure_response.text


def test_ask_falls_back_to_local_when_api_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(config, "dps_provider")
    seed_imported_record(config, "imp_provider", content="POP should keep a local fallback.")
    rebuild_persona_core(config)
    save_project_settings(
        config,
        ProjectSettings(
            provider_mode="api",
            api_base_url="https://api.example.com/v1",
            api_key="sk-test-12345678",
            ask_model="gpt-4.1",
            fallback_to_local_on_error=True,
        ),
    )
    monkeypatch.setattr(
        "pop_cockpit.injector.OpenAICompatibleAskProvider.answer",
        lambda self, prompt_context: (_ for _ in ()).throw(ProviderError("temporary outage")),
    )

    result = ask_question(
        config,
        "How should POP stay resilient?",
        persist=True,
    )

    assert result.status == "created"
    assert result.session is not None
    assert result.session.mode == "dry_run"
    assert result.session.response is None


def test_extract_and_persona_rebuild_fall_back_when_api_is_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(config, "dps_provider_fallback")
    seed_imported_record(config, "imp_extract_provider", content="POP should keep local extraction available.")
    save_project_settings(
        config,
        ProjectSettings(
            provider_mode="api",
            api_base_url="https://api.example.com/v1",
            api_key="sk-test-12345678",
            extract_model="gpt-4.1-mini",
            persona_model="gpt-4.1",
            fallback_to_local_on_error=True,
        ),
    )

    monkeypatch.setattr(
        "pop_cockpit.extractor.ApiDailyExtractionProvider.extract_daily",
        lambda self, request_payload: (_ for _ in ()).throw(ProviderError("extract failed")),
    )
    extraction_result = extract_daily_snapshot(config, "2026-03-22", "2026-03-22", overwrite=True)
    assert extraction_result.status == "created"
    assert extraction_result.snapshot is not None
    assert extraction_result.snapshot.provider_name == "local_fallback"

    monkeypatch.setattr(
        "pop_cockpit.persona.build_persona_core_with_api",
        lambda **kwargs: (_ for _ in ()).throw(ProviderError("persona failed")),
    )
    persona_result = rebuild_persona_core(config)
    assert persona_result.status == "created"
    assert persona_result.persona_core is not None
    assert any("API unavailable" in note for note in persona_result.persona_core.confidence_notes)


def test_dashboard_and_ask_page_show_provider_status(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_daily_snapshot(config, "dps_provider_ui")
    seed_imported_record(config, "imp_provider_ui", content="POP should show engine status clearly.")
    rebuild_persona_core(config)
    save_project_settings(
        config,
        ProjectSettings(
            provider_mode="hybrid",
            api_base_url="https://api.example.com/v1",
            api_key="sk-test-12345678",
            default_model="gpt-4.1",
            ask_model="gpt-4.1-mini",
            last_provider_test_at=datetime(2026, 3, 22, 10, 0, tzinfo=UTC),
            last_provider_test_status="success",
            last_provider_test_message="连接成功",
        ),
    )
    client = TestClient(create_app(config))

    dashboard_response = client.get("/")
    ask_response = client.get("/ask")

    assert dashboard_response.status_code == 200
    assert "AI 引擎状态" in dashboard_response.text
    assert "当前模式：" in dashboard_response.text
    assert "混合模式" in dashboard_response.text
    assert "gpt-4.1" in dashboard_response.text

    assert ask_response.status_code == 200
    assert "本次分析引擎" in ask_response.text
    assert "当前分析引擎：" in ask_response.text
    assert "混合模式" in ask_response.text
