import json
import sqlite3
from pathlib import Path

from pop_cockpit.config import AppConfig
from pop_cockpit.importer import (
    import_file_to_workspace,
    import_folder_to_workspace,
    list_importable_files,
)
from pop_cockpit.storage import ensure_runtime


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


def count_imported_records(database_path: Path) -> int:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute("SELECT COUNT(*) FROM imported_records").fetchone()
    return int(row[0])


def test_list_importable_files_filters_supported_suffixes(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "b.md").write_text("beta", encoding="utf-8")
    (tmp_path / "c.json").write_text("{}", encoding="utf-8")
    (tmp_path / "ignore.csv").write_text("x,y", encoding="utf-8")

    results = list_importable_files(tmp_path)

    assert [path.name for path in results] == ["a.txt", "b.md", "c.json"]


def test_import_text_file_persists_record_and_raw_json(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    source_file = tmp_path / "note.txt"
    source_file.write_text("alpha note", encoding="utf-8")

    summary = import_file_to_workspace(config, source_file)

    assert summary.imported_count == 1
    assert summary.duplicate_count == 0
    assert count_imported_records(config.database_path) == 1
    raw_logs = list(config.raw_logs_dir.glob("*.json"))
    assert len(raw_logs) == 1
    payload = json.loads(raw_logs[0].read_text(encoding="utf-8"))
    assert payload["source_type"] == "text"
    assert payload["content"] == "alpha note"


def test_import_markdown_file_uses_markdown_source_type(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    source_file = tmp_path / "note.md"
    source_file.write_text("# Heading\n\nbody", encoding="utf-8")

    summary = import_file_to_workspace(config, source_file)

    assert summary.imported_count == 1
    assert summary.imported_records[0].source_type == "markdown"


def test_import_json_file_normalizes_content(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    source_file = tmp_path / "note.json"
    source_file.write_text('{"b":2,"a":1}', encoding="utf-8")

    summary = import_file_to_workspace(config, source_file)

    assert summary.imported_count == 1
    assert summary.imported_records[0].source_type == "json"
    assert summary.imported_records[0].content == '{\n  "a": 1,\n  "b": 2\n}'


def test_folder_import_recurses_and_skips_unsupported_files(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    source_dir = tmp_path / "imports"
    nested_dir = source_dir / "nested"
    nested_dir.mkdir(parents=True)
    (source_dir / "one.txt").write_text("one", encoding="utf-8")
    (nested_dir / "two.md").write_text("two", encoding="utf-8")
    (nested_dir / "ignore.png").write_bytes(b"png")

    summary = import_folder_to_workspace(config, source_dir)

    assert summary.imported_count == 2
    assert summary.unsupported_count == 1
    assert summary.skipped_count == 1
    assert count_imported_records(config.database_path) == 2


def test_import_deduplicates_by_content_hash(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    first_file = tmp_path / "first.txt"
    second_file = tmp_path / "second.md"
    first_file.write_text("same content", encoding="utf-8")
    second_file.write_text("same content", encoding="utf-8")

    first_summary = import_file_to_workspace(config, first_file)
    second_summary = import_file_to_workspace(config, second_file)

    assert first_summary.imported_count == 1
    assert second_summary.duplicate_count == 1
    assert second_summary.skipped_count == 1
    assert count_imported_records(config.database_path) == 1
    assert len(list(config.raw_logs_dir.glob("*.json"))) == 1


def test_unsupported_file_returns_readable_skip(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    source_file = tmp_path / "ignore.pdf"
    source_file.write_bytes(b"%PDF-1.4")

    summary = import_file_to_workspace(config, source_file)

    assert summary.imported_count == 0
    assert summary.unsupported_count == 1
    assert summary.skipped_count == 1
    assert "Unsupported file type" in summary.results[0].message
