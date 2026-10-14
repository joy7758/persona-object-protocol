from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pop_cockpit.browser_capture import (
    BROWSER_CAPTURE_REQUIRED_FIELDS,
    BROWSER_CAPTURE_SOURCE_TYPE,
    build_capture_fingerprint,
    browser_capture_endpoint_contract,
    ingest_browser_capture_message,
    normalize_browser_capture_message,
    reset_capture_diagnostics,
)
from pop_cockpit.config import AppConfig
from pop_cockpit.schemas import BrowserCaptureMessage
from pop_cockpit.storage import ensure_runtime, get_connection, list_imported_records
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


def sample_payload(**overrides) -> BrowserCaptureMessage:
    payload = BrowserCaptureMessage(
        role="assistant",
        text="Keep the capture layer thin and local-first.",
        page_url="https://chatgpt.com/c/example",
        conversation_title="Capture Test",
        captured_at=datetime(2026, 3, 22, 12, 0, tzinfo=UTC),
        message_fingerprint="pop-12345-42",
        dom_index=3,
    )
    data = payload.model_dump(mode="python")
    data.update(overrides)
    return BrowserCaptureMessage.model_validate(data)


@pytest.fixture(autouse=True)
def clear_capture_state() -> None:
    reset_capture_diagnostics()


def test_normalize_browser_capture_payload_into_imported_record() -> None:
    record = normalize_browser_capture_message(sample_payload())

    assert record is not None
    assert record.source_type == BROWSER_CAPTURE_SOURCE_TYPE
    assert record.content == "Keep the capture layer thin and local-first."
    assert "browser_capture" in record.tags
    assert record.metadata["role"] == "assistant"
    assert record.metadata["source_entry"] == "browser_capture"


def test_browser_capture_duplicate_suppression(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)

    first = ingest_browser_capture_message(config, sample_payload())
    second = ingest_browser_capture_message(config, sample_payload())

    assert first.status == "imported"
    assert second.status == "duplicate"
    with get_connection(config.database_path) as connection:
        records = list_imported_records(connection, source_type=BROWSER_CAPTURE_SOURCE_TYPE)
    assert len(records) == 1


def test_capture_ingestion_endpoint_success_response(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    client = TestClient(create_app(config))

    response = client.post(
        "/api/capture/chat-message",
        json=sample_payload().model_dump(mode="json"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "imported"
    assert payload["source_type"] == BROWSER_CAPTURE_SOURCE_TYPE
    assert payload["record_id"]


def test_capture_status_endpoint_reports_recent_count(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    ingest_browser_capture_message(config, sample_payload())
    client = TestClient(create_app(config))

    response = client.get("/api/capture/status?source=extension")

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend_alive"] is True
    assert payload["capture_endpoint_available"] is True
    assert payload["extension_connected"] is True
    assert payload["last_capture_status"] == "imported"
    assert payload["recent_captured_count"] == 1
    assert payload["expected_frontend_origin"] == [
        "https://chatgpt.com",
        "https://chat.openai.com",
    ]
    assert payload["browser_captured_count_recent"] == 1
    assert payload["contract"]["required_fields"] == BROWSER_CAPTURE_REQUIRED_FIELDS


def test_browser_capture_endpoint_contract_documents_payload_shape() -> None:
    contract = browser_capture_endpoint_contract()

    assert contract["required_fields"] == BROWSER_CAPTURE_REQUIRED_FIELDS
    assert contract["source_type"] == BROWSER_CAPTURE_SOURCE_TYPE
    assert contract["response_statuses"] == ["imported", "duplicate", "skipped", "error"]


def test_browser_capture_content_hash_is_deterministic() -> None:
    first = normalize_browser_capture_message(sample_payload())
    second = normalize_browser_capture_message(sample_payload())

    assert first is not None and second is not None
    assert first.content_hash == second.content_hash


def test_recent_capture_events_endpoint_returns_latest_events(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    client = TestClient(create_app(config))
    client.post("/api/capture/chat-message", json=sample_payload().model_dump(mode="json"))

    response = client.get("/api/capture/recent")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["events"][0]["status"] == "imported"
    assert payload["events"][0]["preview"].startswith("Keep the capture layer")


def test_capture_test_endpoint_creates_self_test_message(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    client = TestClient(create_app(config))

    response = client.post("/api/capture/test")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "imported"
    assert "测试采集成功" in payload["message"]


def test_build_capture_fingerprint_is_deterministic() -> None:
    first = build_capture_fingerprint(role="assistant", text="Hello POP", dom_index=2)
    second = build_capture_fingerprint(role="assistant", text="Hello POP", dom_index=2)

    assert first == second
