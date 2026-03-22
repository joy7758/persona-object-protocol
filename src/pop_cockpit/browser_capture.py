from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime
from datetime import timedelta
from threading import Lock
from typing import Any

from pop_cockpit.config import AppConfig
from pop_cockpit.schemas import (
    CaptureEventRecord,
    BrowserCaptureIngestionResult,
    BrowserCaptureMessage,
    CaptureStatusResponse,
    ImportedRecord,
)
from pop_cockpit.storage import get_connection, get_imported_record_by_hash, insert_imported_record, list_imported_records
from pop_cockpit.utils import new_id, sha256_text, utc_now, write_json

BROWSER_CAPTURE_SOURCE_TYPE = "chatgpt_browser_capture"
BROWSER_CAPTURE_REQUIRED_FIELDS = [
    "role",
    "text",
    "page_url",
    "conversation_title",
    "captured_at",
    "message_fingerprint",
]
EXPECTED_FRONTEND_ORIGINS = [
    "https://chatgpt.com",
    "https://chat.openai.com",
]
_CAPTURE_EVENT_LIMIT = 20
_capture_events: deque[CaptureEventRecord] = deque(maxlen=_CAPTURE_EVENT_LIMIT)
_capture_events_lock = Lock()
_last_extension_heartbeat_at: str | None = None
_extension_heartbeat_lock = Lock()
logger = logging.getLogger(__name__)


def normalize_browser_capture_message(payload: BrowserCaptureMessage) -> ImportedRecord | None:
    normalized_text = _normalize_capture_text(payload.text)
    if not normalized_text:
        return None

    normalized_role = _normalize_role(payload.role)
    content_hash = sha256_text(
        json.dumps(
            {
                "source_type": BROWSER_CAPTURE_SOURCE_TYPE,
                "page_url": payload.page_url,
                "role": normalized_role,
                "message_fingerprint": payload.message_fingerprint,
                "content": normalized_text,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return ImportedRecord(
        id=new_id("imp"),
        source_type=BROWSER_CAPTURE_SOURCE_TYPE,
        source_path=payload.page_url,
        imported_at=utc_now(),
        content=normalized_text,
        content_hash=content_hash,
        tags=[
            "browser_capture",
            "origin:chatgpt",
            f"role:{normalized_role}",
        ],
        metadata={
            "role": normalized_role,
            "page_url": payload.page_url,
            "conversation_title": payload.conversation_title.strip(),
            "captured_at": payload.captured_at.isoformat(),
            "message_fingerprint": payload.message_fingerprint,
            "dom_index": payload.dom_index,
            "source_entry": "browser_capture",
        },
    )


def ingest_browser_capture_message(
    config: AppConfig,
    payload: BrowserCaptureMessage,
) -> BrowserCaptureIngestionResult:
    record_extension_heartbeat()
    record = normalize_browser_capture_message(payload)
    if record is None:
        result = BrowserCaptureIngestionResult(
            status="skipped",
            skipped=True,
            reason="Captured message text was empty after normalization.",
        )
        _record_capture_event(payload=payload, result=result)
        return result

    try:
        with get_connection(config.database_path) as connection:
            existing = get_imported_record_by_hash(connection, record.content_hash)
            if existing is not None:
                result = BrowserCaptureIngestionResult(
                    status="duplicate",
                    duplicate=True,
                    reason=f"Matches existing record {existing.id}.",
                    record_id=existing.id,
                )
                _record_capture_event(payload=payload, result=result)
                return result

            insert_imported_record(connection, record)
            write_json(config.raw_logs_dir / f"{record.id}.json", record.model_dump(mode="json"))
    except Exception as exc:
        result = BrowserCaptureIngestionResult(
            status="error",
            reason=f"Capture ingestion failed: {exc}",
        )
        _record_capture_event(payload=payload, result=result)
        return result

    result = BrowserCaptureIngestionResult(
        status="imported",
        imported=True,
        reason="Captured message saved.",
        record_id=record.id,
    )
    _record_capture_event(payload=payload, result=result)
    return result


def capture_status(config: AppConfig) -> CaptureStatusResponse:
    try:
        with get_connection(config.database_path) as connection:
            records = [
                record
                for record in list_imported_records(connection, source_type=BROWSER_CAPTURE_SOURCE_TYPE)
            ]
        backend_alive = True
        capture_endpoint_available = True
        status = "ok"
        status_error = ""
    except Exception as exc:
        records = []
        backend_alive = True
        capture_endpoint_available = False
        status = "degraded"
        status_error = f"采集状态读取失败：{exc}"
    now = utc_now()
    recent_cutoff = now - timedelta(minutes=10)
    recent_events = [
        event
        for event in list_recent_capture_events()
        if _parse_event_timestamp(event.timestamp) >= recent_cutoff
        and event.status in {"imported", "duplicate"}
    ]
    latest_event = list_recent_capture_events(limit=1)
    last_event = latest_event[0] if latest_event else None
    latest_capture = last_event.timestamp if last_event else (
        max(record.imported_at for record in records).isoformat() if records else None
    )
    last_error = next(
        (event for event in list_recent_capture_events() if event.status == "error"),
        None,
    )
    last_error_message = status_error or (last_error.reason if last_error is not None else "")
    last_extension_heartbeat_at = get_last_extension_heartbeat_at()
    extension_connected = False
    if last_extension_heartbeat_at:
        try:
            extension_connected = (
                _parse_event_timestamp(last_extension_heartbeat_at) >= now - timedelta(seconds=45)
            )
        except ValueError:
            extension_connected = False
    return CaptureStatusResponse(
        status=status,
        backend_alive=backend_alive,
        capture_endpoint_available=capture_endpoint_available,
        extension_connected=extension_connected,
        last_extension_heartbeat_at=last_extension_heartbeat_at,
        last_capture_at=latest_capture,
        last_capture_status=last_event.status if last_event is not None else "idle",
        last_error_message=last_error_message,
        recent_captured_count=len(recent_events),
        expected_frontend_origin=EXPECTED_FRONTEND_ORIGINS.copy(),
        browser_captured_count_recent=len(recent_events),
        latest_browser_capture_at=latest_capture,
    )


def browser_capture_endpoint_contract() -> dict[str, Any]:
    return {
        "required_fields": BROWSER_CAPTURE_REQUIRED_FIELDS,
        "source_type": BROWSER_CAPTURE_SOURCE_TYPE,
        "response_statuses": ["imported", "duplicate", "skipped", "error"],
    }


def list_recent_capture_events(*, limit: int = _CAPTURE_EVENT_LIMIT) -> list[CaptureEventRecord]:
    with _capture_events_lock:
        events = list(_capture_events)
    return list(reversed(events[-limit:]))


def record_extension_heartbeat() -> str:
    heartbeat_at = utc_now().isoformat()
    global _last_extension_heartbeat_at
    with _extension_heartbeat_lock:
        _last_extension_heartbeat_at = heartbeat_at
    return heartbeat_at


def get_last_extension_heartbeat_at() -> str | None:
    with _extension_heartbeat_lock:
        return _last_extension_heartbeat_at


def run_capture_self_test(config: AppConfig) -> BrowserCaptureIngestionResult:
    now = utc_now()
    fingerprint = build_capture_fingerprint(
        role="assistant",
        text=f"POP capture self-test at {now.isoformat()}",
        dom_index=0,
    )
    payload = BrowserCaptureMessage(
        role="assistant",
        text=f"POP capture self-test at {now.isoformat()}",
        page_url="http://127.0.0.1:8765/self-test",
        conversation_title="POP Self Test",
        captured_at=now,
        message_fingerprint=fingerprint,
        dom_index=0,
    )
    return ingest_browser_capture_message(config, payload)


def build_capture_fingerprint(*, role: str, text: str, dom_index: int | None) -> str:
    basis = "::".join(
        [
            _normalize_role(role),
            _normalize_capture_text(text),
            str(dom_index if dom_index is not None else -1),
        ]
    )
    return f"pop-{sha256_text(basis)[:20]}"


def reset_capture_diagnostics() -> None:
    global _last_extension_heartbeat_at
    with _capture_events_lock:
        _capture_events.clear()
    with _extension_heartbeat_lock:
        _last_extension_heartbeat_at = None


def _normalize_capture_text(value: str) -> str:
    return "\n".join(line.strip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()


def _normalize_role(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"user", "assistant", "system", "tool"}:
        return normalized
    return "unknown"


def _record_capture_event(
    *,
    payload: BrowserCaptureMessage,
    result: BrowserCaptureIngestionResult,
) -> None:
    event = CaptureEventRecord(
        timestamp=utc_now().isoformat(),
        role=_normalize_role(payload.role),
        preview=_preview_text(payload.text),
        status=result.status,
        message_fingerprint=payload.message_fingerprint,
        record_id=result.record_id,
        reason=result.reason,
    )
    with _capture_events_lock:
        _capture_events.append(event)
    logger.info(
        "browser_capture status=%s role=%s preview=%s reason=%s",
        event.status,
        event.role,
        event.preview,
        event.reason,
    )


def _preview_text(value: str, max_chars: int = 50) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars].rstrip()}..."


def _parse_event_timestamp(value: str):
    normalized = value
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    return datetime.fromisoformat(normalized)
