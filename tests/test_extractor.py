import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from pop_cockpit.config import AppConfig
from pop_cockpit.extractor import (
    backfill_daily_snapshots,
    extract_daily_snapshot,
    resolve_effective_event_date,
    resolve_effective_event_timestamp,
)
from pop_cockpit.providers import LocalFallbackDailyExtractionProvider
from pop_cockpit.prompts import build_daily_extraction_prompt
from pop_cockpit.schemas import DateRange, DailyExtractionRequest, ImportedRecord
from pop_cockpit.storage import ensure_runtime, get_connection, insert_imported_record


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
    imported_at: datetime,
    content: str,
    source_type: str = "text",
    metadata: dict | None = None,
) -> None:
    ensure_runtime(config)
    record = ImportedRecord(
        id=record_id,
        source_type=source_type,
        source_path=f"/tmp/{record_id}.{source_type}",
        imported_at=imported_at,
        content=content,
        content_hash=f"hash-{record_id}",
        tags=[],
        metadata=metadata or {},
    )
    with get_connection(config.database_path) as connection:
        insert_imported_record(connection, record)


def snapshot_rows(config: AppConfig) -> list[tuple]:
    with sqlite3.connect(config.database_path) as connection:
        return connection.execute(
            """
            SELECT date_from, date_to, snapshot_scope, payload_json
            FROM daily_persona_snapshots
            ORDER BY date_from ASC, snapshot_scope ASC, created_at ASC
            """
        ).fetchall()


def test_effective_timestamp_prefers_metadata_created_at() -> None:
    record = ImportedRecord(
        id="imp_meta",
        source_type="chatgpt_export",
        source_path="/tmp/imp_meta.json",
        imported_at=datetime(2026, 3, 21, 10, 0, tzinfo=UTC),
        content="Historical record",
        content_hash="hash-meta",
        tags=[],
        metadata={"created_at": "2024-03-21T06:03:21+00:00"},
    )

    resolved = resolve_effective_event_timestamp(record)

    assert resolved == datetime(2024, 3, 21, 6, 3, 21, tzinfo=UTC)
    assert resolve_effective_event_date(record) == "2024-03-21"


def test_effective_timestamp_falls_back_to_imported_at() -> None:
    record = ImportedRecord(
        id="imp_fallback",
        source_type="text",
        source_path="/tmp/imp_fallback.txt",
        imported_at=datetime(2026, 3, 21, 10, 0, tzinfo=UTC),
        content="Fallback record",
        content_hash="hash-fallback",
        tags=[],
        metadata={},
    )

    resolved = resolve_effective_event_timestamp(record)

    assert resolved == datetime(2026, 3, 21, 10, 0, tzinfo=UTC)
    assert resolve_effective_event_date(record) == "2026-03-21"


def test_extract_daily_uses_source_time_when_available(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_imported_record(
        config,
        record_id="imp_hist",
        imported_at=datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
        content="Priority: preserve original event dates.",
        source_type="chatgpt_export",
        metadata={"created_at": "2024-03-21T06:03:21+00:00"},
    )

    result = extract_daily_snapshot(config, "2024-03-21", "2024-03-21")

    assert result.status == "created"
    assert result.snapshot is not None
    assert result.snapshot.source_record_ids == ["imp_hist"]


def test_extract_daily_with_no_records_returns_empty_result(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)

    result = extract_daily_snapshot(config, "2026-03-21", "2026-03-22")

    assert result.status == "empty"
    assert result.snapshot is None
    assert "No imported records found" in result.message


def test_backfill_over_multiple_days_generates_distinct_snapshots(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_imported_record(
        config,
        record_id="imp_day1",
        imported_at=datetime(2026, 3, 22, 9, 0, tzinfo=UTC),
        content="Priority: finish day one planning.",
        source_type="chatgpt_export",
        metadata={"created_at": "2024-03-21T06:03:21+00:00"},
    )
    seed_imported_record(
        config,
        record_id="imp_day2",
        imported_at=datetime(2026, 3, 22, 9, 5, tzinfo=UTC),
        content="Decision: keep day two focused and readable.",
        source_type="chatgpt_export",
        metadata={"created_at": "2024-03-22T06:03:21+00:00"},
    )

    result = backfill_daily_snapshots(config, "2024-03-21", "2024-03-22")

    assert result.days_scanned == 2
    assert result.days_generated == 2
    assert result.days_skipped == 0
    assert result.total_source_records_used == 2
    assert result.generated_dates == ["2024-03-21", "2024-03-22"]
    assert len(snapshot_rows(config)) == 2


def test_backfill_skips_empty_days(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_imported_record(
        config,
        record_id="imp_sparse",
        imported_at=datetime(2026, 3, 22, 10, 0, tzinfo=UTC),
        content="Current focus: sparse historical record.",
        metadata={"created_at": "2024-03-21T06:03:21+00:00"},
    )

    result = backfill_daily_snapshots(config, "2024-03-21", "2024-03-23")

    assert result.days_scanned == 3
    assert result.days_generated == 1
    assert result.days_skipped == 2
    assert result.generated_dates == ["2024-03-21"]


def test_backfill_overwrite_replaces_existing_snapshot_rows(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_imported_record(
        config,
        record_id="imp_overwrite",
        imported_at=datetime(2026, 3, 22, 11, 0, tzinfo=UTC),
        content="Priority: keep overwrite deterministic.",
        metadata={"created_at": "2024-03-21T06:03:21+00:00"},
    )

    first = backfill_daily_snapshots(config, "2024-03-21", "2024-03-21")
    second = backfill_daily_snapshots(config, "2024-03-21", "2024-03-21")
    third = backfill_daily_snapshots(config, "2024-03-21", "2024-03-21", overwrite=True)

    assert first.days_generated == 1
    assert second.days_generated == 0
    assert second.days_skipped == 1
    assert third.days_generated == 1
    assert len(snapshot_rows(config)) == 1


def test_backfill_source_type_filter_limits_records(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_imported_record(
        config,
        record_id="imp_chatgpt",
        imported_at=datetime(2026, 3, 22, 11, 0, tzinfo=UTC),
        content="Priority: import ChatGPT history.",
        source_type="chatgpt_export",
        metadata={"created_at": "2024-03-21T06:03:21+00:00"},
    )
    seed_imported_record(
        config,
        record_id="imp_text",
        imported_at=datetime(2026, 3, 22, 11, 5, tzinfo=UTC),
        content="Priority: plain text note.",
        source_type="text",
    )

    result = backfill_daily_snapshots(
        config,
        "2024-03-21",
        "2026-03-22",
        source_type="chatgpt_export",
    )

    rows = snapshot_rows(config)
    assert result.days_generated == 1
    assert rows[0][2] == "source_type:chatgpt_export"
    payload = json.loads(rows[0][3])
    assert payload["source_record_ids"] == ["imp_chatgpt"]
    assert payload["metadata"]["source_type_filter"] == "chatgpt_export"


def test_daily_extraction_output_is_deterministic_for_same_source_set(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    seed_imported_record(
        config,
        record_id="imp_a",
        imported_at=datetime(2026, 3, 22, 12, 0, tzinfo=UTC),
        content="Priority: build a local-first system.\nWe should test and verify the output.",
        metadata={"created_at": "2024-03-21T06:03:21+00:00"},
    )
    seed_imported_record(
        config,
        record_id="imp_b",
        imported_at=datetime(2026, 3, 22, 12, 5, tzinfo=UTC),
        content="Decision: keep the design simple.\nI feel confident about the plan.",
        metadata={"created_at": "2024-03-21T07:03:21+00:00"},
    )

    first = extract_daily_snapshot(config, "2024-03-21", "2024-03-21")
    second = extract_daily_snapshot(config, "2024-03-21", "2024-03-21", overwrite=True)

    assert first.snapshot is not None
    assert second.snapshot is not None
    first_payload = first.snapshot.model_dump(exclude={"id", "created_at"})
    second_payload = second.snapshot.model_dump(exclude={"id", "created_at"})
    assert first_payload == second_payload


def test_local_fallback_provider_is_deterministic() -> None:
    record = ImportedRecord(
        id="imp_deterministic",
        source_type="text",
        source_path="/tmp/imp_deterministic.txt",
        imported_at=datetime(2026, 3, 21, 10, 0, tzinfo=UTC),
        content="Priority: build a local-first system.\nWe should test and verify the output.",
        content_hash="hash-deterministic",
        tags=[],
    )
    request = DailyExtractionRequest(
        date_range=DateRange(date_from="2026-03-21", date_to="2026-03-21"),
        records=[record],
        prompt=build_daily_extraction_prompt([record], "2026-03-21", "2026-03-21"),
    )
    provider = LocalFallbackDailyExtractionProvider()

    first = provider.extract_daily(request)
    second = provider.extract_daily(request)

    assert first.model_dump() == second.model_dump()
