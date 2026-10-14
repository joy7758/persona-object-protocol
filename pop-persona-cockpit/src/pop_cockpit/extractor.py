from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from pop_cockpit.config import AppConfig
from pop_cockpit.llm_api import ApiDailyExtractionProvider, ProviderError, build_provider_client, resolve_task_model
from pop_cockpit.prompts import build_daily_extraction_prompt
from pop_cockpit.providers import DailyExtractionProvider, LocalFallbackDailyExtractionProvider
from pop_cockpit.schemas import DateRange, DailyExtractionRequest, DailyPersonaSnapshot
from pop_cockpit.settings import load_project_settings
from pop_cockpit.storage import (
    delete_daily_persona_snapshots,
    find_daily_persona_snapshot,
    get_connection,
    insert_daily_persona_snapshot,
    list_imported_records,
)
from pop_cockpit.utils import new_id, utc_now, write_json


@dataclass(slots=True)
class DailyExtractionResult:
    status: str
    message: str
    snapshot: DailyPersonaSnapshot | None = None
    json_path: Path | None = None
    markdown_path: Path | None = None


@dataclass(slots=True)
class BackfillResult:
    status: str
    message: str
    days_scanned: int
    days_generated: int
    days_skipped: int
    total_source_records_used: int
    generated_dates: list[str]


def extract_daily_snapshot(
    config: AppConfig,
    date_from: str,
    date_to: str,
    provider: DailyExtractionProvider | None = None,
    overwrite: bool = False,
    source_type: str | None = None,
) -> DailyExtractionResult:
    _validate_date(date_from)
    _validate_date(date_to)
    if date_from > date_to:
        raise ValueError("The start date must be on or before the end date.")

    with get_connection(config.database_path) as connection:
        records = list_imported_records(connection, source_type=source_type)
        filtered_records = filter_records_by_effective_date_range(records, date_from, date_to)
        return _extract_daily_snapshot_from_records(
            connection=connection,
            config=config,
            date_from=date_from,
            date_to=date_to,
            records=filtered_records,
            provider=provider,
            overwrite=overwrite,
            source_type=source_type,
        )


def backfill_daily_snapshots(
    config: AppConfig,
    date_from: str,
    date_to: str,
    provider: DailyExtractionProvider | None = None,
    overwrite: bool = False,
    source_type: str | None = None,
) -> BackfillResult:
    _validate_date(date_from)
    _validate_date(date_to)
    start_date = date.fromisoformat(date_from)
    end_date = date.fromisoformat(date_to)
    if start_date > end_date:
        raise ValueError("The start date must be on or before the end date.")

    days_scanned = (end_date - start_date).days + 1
    with get_connection(config.database_path) as connection:
        all_records = list_imported_records(connection, source_type=source_type)
        records_by_day = bucket_records_by_effective_date(all_records, date_from, date_to)

        days_generated = 0
        days_skipped = 0
        total_source_records_used = 0
        generated_dates: list[str] = []
        current_date = start_date
        while current_date <= end_date:
            day_key = current_date.isoformat()
            day_records = records_by_day.get(day_key, [])
            if not day_records:
                days_skipped += 1
                current_date += timedelta(days=1)
                continue

            result = _extract_daily_snapshot_from_records(
                connection=connection,
                config=config,
                date_from=day_key,
                date_to=day_key,
                records=day_records,
                provider=provider,
                overwrite=overwrite,
                source_type=source_type,
            )
            if result.status == "created":
                days_generated += 1
                total_source_records_used += len(day_records)
                generated_dates.append(day_key)
            else:
                days_skipped += 1
            current_date += timedelta(days=1)

    return BackfillResult(
        status="completed",
        message=f"Backfill completed for {date_from} to {date_to}.",
        days_scanned=days_scanned,
        days_generated=days_generated,
        days_skipped=days_skipped,
        total_source_records_used=total_source_records_used,
        generated_dates=generated_dates,
    )


def format_daily_extraction_result(result: DailyExtractionResult) -> str:
    lines = [result.message]
    if result.snapshot is None:
        return "\n".join(lines)

    lines.extend(
        [
            f"snapshot_id: {result.snapshot.id}",
            f"date_range: {result.snapshot.date_range.date_from} -> {result.snapshot.date_range.date_to}",
            f"source_records: {len(result.snapshot.source_record_ids)}",
            f"provider: {result.snapshot.provider_name}",
        ]
    )
    if result.json_path is not None:
        lines.append(f"json: {result.json_path}")
    if result.markdown_path is not None:
        lines.append(f"markdown: {result.markdown_path}")
    return "\n".join(lines)


def format_backfill_result(result: BackfillResult) -> str:
    lines = [
        result.message,
        f"days_scanned: {result.days_scanned}",
        f"days_generated: {result.days_generated}",
        f"days_skipped: {result.days_skipped}",
        f"total_source_records_used: {result.total_source_records_used}",
    ]
    if result.generated_dates:
        lines.append(f"generated_dates: {', '.join(result.generated_dates)}")
    return "\n".join(lines)


def write_daily_snapshot_files(
    config: AppConfig, snapshot: DailyPersonaSnapshot
) -> tuple[Path, Path]:
    snapshot_scope = str(snapshot.metadata.get("snapshot_scope", "all"))
    base_name = snapshot_base_name(
        snapshot.date_range.date_from,
        snapshot.date_range.date_to,
        snapshot_scope=snapshot_scope,
    )
    json_path = config.daily_notes_dir / f"{base_name}.json"
    markdown_path = config.daily_notes_dir / f"{base_name}.md"
    write_json(json_path, snapshot.model_dump(mode="json"))
    markdown_path.write_text(render_daily_snapshot_markdown(snapshot), encoding="utf-8")
    return json_path, markdown_path


def render_daily_snapshot_markdown(snapshot: DailyPersonaSnapshot) -> str:
    sections = [
        "# Daily Persona Snapshot",
        "",
        f"- Date range: {snapshot.date_range.date_from} to {snapshot.date_range.date_to}",
        f"- Snapshot ID: {snapshot.id}",
        f"- Created at: {snapshot.created_at.isoformat()}",
        f"- Provider: {snapshot.provider_name}",
        f"- Event time policy: {snapshot.metadata.get('event_time_policy', 'metadata.created_at -> imported_at')}",
        f"- Source record IDs: {', '.join(snapshot.source_record_ids)}",
        "",
        "## Goal Priority",
        _render_list(snapshot.goal_priority),
        "",
        "## Current Focus",
        _render_list(snapshot.current_focus),
        "",
        "## Decision Style",
        snapshot.decision_style or "No strong signal detected.",
        "",
        "## Risk Profile",
        snapshot.risk_profile or "No strong signal detected.",
        "",
        "## Recurring Topics",
        _render_list(snapshot.recurring_topics),
        "",
        "## Stable Biases",
        _render_list(snapshot.stable_biases),
        "",
        "## Emotional Signals",
        _render_list(snapshot.emotional_signals),
        "",
        "## New Traits",
        _render_list(snapshot.new_traits),
        "",
        "## Important Decisions",
        _render_list(snapshot.important_decisions),
        "",
        "## Confidence Notes",
        _render_list(snapshot.confidence_notes),
    ]
    return "\n".join(sections).strip() + "\n"


def _render_list(items: list[str]) -> str:
    if not items:
        return "- None detected"
    return "\n".join(f"- {item}" for item in items)


def resolve_effective_event_timestamp(record) -> datetime:
    """
    Prefer the original event timestamp stored in metadata.created_at.
    Fallback to imported_at when metadata is missing or malformed.
    """
    metadata_created_at = record.metadata.get("created_at")
    parsed_metadata_time = _parse_iso_datetime(metadata_created_at)
    if parsed_metadata_time is not None:
        return parsed_metadata_time
    return _normalize_datetime(record.imported_at)


def resolve_effective_event_date(record) -> str:
    return resolve_effective_event_timestamp(record).date().isoformat()


def filter_records_by_effective_date_range(records, date_from: str, date_to: str):
    filtered = [
        record
        for record in records
        if date_from <= resolve_effective_event_date(record) <= date_to
    ]
    return sorted(
        filtered,
        key=lambda record: (resolve_effective_event_timestamp(record), record.id),
    )


def bucket_records_by_effective_date(records, date_from: str, date_to: str) -> dict[str, list]:
    buckets: dict[str, list] = defaultdict(list)
    for record in filter_records_by_effective_date_range(records, date_from, date_to):
        buckets[resolve_effective_event_date(record)].append(record)
    return dict(buckets)


def snapshot_base_name(date_from: str, date_to: str, snapshot_scope: str) -> str:
    base_name = f"daily_snapshot_{date_from}_to_{date_to}"
    if snapshot_scope == "all":
        return base_name
    scope_label = snapshot_scope.replace("source_type:", "").replace("/", "_").replace(" ", "_")
    return f"{base_name}__{scope_label}"


def build_snapshot_scope(source_type: str | None) -> str:
    return f"source_type:{source_type}" if source_type else "all"


def _validate_date(value: str) -> None:
    date.fromisoformat(value)


def _extract_daily_snapshot_from_records(
    *,
    connection,
    config: AppConfig,
    date_from: str,
    date_to: str,
    records,
    provider: DailyExtractionProvider | None,
    overwrite: bool,
    source_type: str | None,
) -> DailyExtractionResult:
    if not records:
        return DailyExtractionResult(
            status="empty",
            message=f"No imported records found for {date_from} to {date_to}.",
        )

    snapshot_scope = build_snapshot_scope(source_type)
    existing_snapshot = find_daily_persona_snapshot(
        connection,
        date_from=date_from,
        date_to=date_to,
        snapshot_scope=snapshot_scope,
    )
    if existing_snapshot is not None and not overwrite:
        return DailyExtractionResult(
            status="skipped",
            message=(
                f"Daily snapshot already exists for {date_from} to {date_to} "
                f"with scope {snapshot_scope}."
            ),
        )

    if overwrite:
        delete_daily_persona_snapshots(
            connection,
            date_from=date_from,
            date_to=date_to,
            snapshot_scope=snapshot_scope,
        )

    request = DailyExtractionRequest(
        date_range=DateRange(date_from=date_from, date_to=date_to),
        records=records,
        prompt=build_daily_extraction_prompt(records, date_from, date_to),
    )
    settings = load_project_settings(config)
    selected_provider = provider or _provider_from_settings(settings)
    try:
        draft = selected_provider.extract_daily(request)
    except ProviderError as exc:
        if selected_provider is not provider and settings.fallback_to_local_on_error:
            selected_provider = LocalFallbackDailyExtractionProvider()
            draft = selected_provider.extract_daily(request)
        else:
            return DailyExtractionResult(
                status="error",
                message=f"AI 每日蒸馏失败：{exc}",
            )
    draft_payload = draft.model_dump()
    draft_payload["metadata"] = {
        **draft.metadata,
        "snapshot_scope": snapshot_scope,
        "source_type_filter": source_type,
        "event_time_policy": "metadata.created_at -> imported_at",
    }
    snapshot = DailyPersonaSnapshot(
        id=new_id("dps"),
        created_at=utc_now(),
        **draft_payload,
    )

    json_path, markdown_path = write_daily_snapshot_files(config, snapshot)
    insert_daily_persona_snapshot(connection, snapshot, markdown_path, snapshot_scope)
    return DailyExtractionResult(
        status="created",
        message=f"Created daily snapshot for {date_from} to {date_to}.",
        snapshot=snapshot,
        json_path=json_path,
        markdown_path=markdown_path,
    )


def _provider_from_settings(settings) -> DailyExtractionProvider:
    model = resolve_task_model(settings, "extract")
    if settings.provider_mode in {"api", "hybrid"} and model:
        return ApiDailyExtractionProvider(
            client=build_provider_client(settings),
            model=model,
        )
    return LocalFallbackDailyExtractionProvider()


def _parse_iso_datetime(value) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed_date = date.fromisoformat(normalized)
        except ValueError:
            return None
        parsed = datetime.combine(parsed_date, datetime.min.time(), tzinfo=UTC)
    return _normalize_datetime(parsed)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
