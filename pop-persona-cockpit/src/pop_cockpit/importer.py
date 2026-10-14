from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from pop_cockpit.config import AppConfig
from pop_cockpit.schemas import ImportedRecord
from pop_cockpit.storage import get_connection, get_imported_record_by_hash, insert_imported_record
from pop_cockpit.utils import new_id, sha256_text, utc_now, write_json

SUPPORTED_IMPORT_SUFFIXES = {
    ".txt": "text",
    ".md": "markdown",
    ".json": "json",
}


@dataclass(slots=True)
class ImportFileResult:
    path: Path
    status: str
    message: str
    record: ImportedRecord | None = None


@dataclass(slots=True)
class ImportSummary:
    target_path: Path
    imported_count: int = 0
    skipped_count: int = 0
    duplicate_count: int = 0
    unsupported_count: int = 0
    results: list[ImportFileResult] = field(default_factory=list)

    def add_result(self, result: ImportFileResult) -> None:
        self.results.append(result)
        if result.status == "imported":
            self.imported_count += 1
            return
        if result.status == "duplicate":
            self.duplicate_count += 1
            self.skipped_count += 1
            return
        if result.status == "unsupported":
            self.unsupported_count += 1
            self.skipped_count += 1
            return
        self.skipped_count += 1

    @property
    def imported_records(self) -> list[ImportedRecord]:
        return [result.record for result in self.results if result.record is not None]


def list_importable_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() in SUPPORTED_IMPORT_SUFFIXES else []

    if not path.is_dir():
        return []

    return sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_IMPORT_SUFFIXES
    )


def list_unsupported_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() not in SUPPORTED_IMPORT_SUFFIXES else []

    if not path.is_dir():
        return []

    return sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() not in SUPPORTED_IMPORT_SUFFIXES
    )


def import_file_to_workspace(config: AppConfig, path: Path) -> ImportSummary:
    target_path = path.expanduser().resolve()
    if not target_path.exists():
        raise FileNotFoundError(f"File not found: {target_path}")
    if not target_path.is_file():
        raise IsADirectoryError(f"Expected a file path, received: {target_path}")

    summary = ImportSummary(target_path=target_path)
    if target_path.suffix.lower() not in SUPPORTED_IMPORT_SUFFIXES:
        summary.add_result(
            ImportFileResult(
                path=target_path,
                status="unsupported",
                message=f"Unsupported file type: {target_path.suffix or '<no extension>'}",
            )
        )
        return summary

    with get_connection(config.database_path) as connection:
        summary.add_result(_import_supported_file(connection, config, target_path))
    return summary


def import_folder_to_workspace(config: AppConfig, path: Path) -> ImportSummary:
    target_path = path.expanduser().resolve()
    if not target_path.exists():
        raise FileNotFoundError(f"Folder not found: {target_path}")
    if not target_path.is_dir():
        raise NotADirectoryError(f"Expected a folder path, received: {target_path}")

    summary = ImportSummary(target_path=target_path)
    supported_files = list_importable_files(target_path)
    unsupported_files = list_unsupported_files(target_path)

    for unsupported_path in unsupported_files:
        summary.add_result(
            ImportFileResult(
                path=unsupported_path,
                status="unsupported",
                message=f"Unsupported file type: {unsupported_path.suffix or '<no extension>'}",
            )
        )

    with get_connection(config.database_path) as connection:
        for supported_path in supported_files:
            summary.add_result(_import_supported_file(connection, config, supported_path))

    return summary


def format_import_summary(summary: ImportSummary) -> str:
    lines = [
        "Import summary",
        f"target: {summary.target_path}",
        f"imported: {summary.imported_count}",
        f"skipped: {summary.skipped_count}",
        f"duplicates: {summary.duplicate_count}",
        f"unsupported: {summary.unsupported_count}",
    ]
    for result in summary.results:
        lines.append(f"- {result.status}: {result.path} ({result.message})")
    return "\n".join(lines)


def _import_supported_file(connection, config: AppConfig, path: Path) -> ImportFileResult:
    record = _build_imported_record(path)
    existing_record = get_imported_record_by_hash(connection, record.content_hash)
    if existing_record is not None:
        return ImportFileResult(
            path=path,
            status="duplicate",
            message=f"Matches existing record {existing_record.id}",
        )

    try:
        insert_imported_record(connection, record)
    except sqlite3.IntegrityError:
        existing_record = get_imported_record_by_hash(connection, record.content_hash)
        duplicate_message = "Matches existing imported content"
        if existing_record is not None:
            duplicate_message = f"Matches existing record {existing_record.id}"
        return ImportFileResult(
            path=path,
            status="duplicate",
            message=duplicate_message,
        )

    _write_raw_log_copy(config, record)
    return ImportFileResult(
        path=path,
        status="imported",
        message=f"Saved as {record.id}",
        record=record,
    )


def _build_imported_record(path: Path) -> ImportedRecord:
    source_type = SUPPORTED_IMPORT_SUFFIXES[path.suffix.lower()]
    content = _normalize_file_content(path)
    return ImportedRecord(
        id=new_id("imp"),
        source_type=source_type,
        source_path=str(path),
        imported_at=utc_now(),
        content=content,
        content_hash=sha256_text(content),
        tags=[],
        metadata={},
    )


def _normalize_file_content(path: Path) -> str:
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    normalized_text = _normalize_newlines(raw_text)
    if path.suffix.lower() != ".json":
        return normalized_text.strip()

    try:
        payload = json.loads(normalized_text)
    except json.JSONDecodeError:
        return normalized_text.strip()
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _write_raw_log_copy(config: AppConfig, record: ImportedRecord) -> None:
    write_json(
        config.raw_logs_dir / f"{record.id}.json",
        record.model_dump(mode="json"),
    )
