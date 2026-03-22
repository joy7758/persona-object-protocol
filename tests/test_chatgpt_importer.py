import json
import sqlite3
import zipfile
from pathlib import Path

from pop_cockpit.chatgpt_importer import import_chatgpt_export, normalize_chatgpt_message
from pop_cockpit.config import AppConfig
from pop_cockpit.storage import ensure_runtime
from pop_cockpit.utils import utc_now


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


def write_mock_conversations_json(target_dir: Path, payload: list[dict]) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "conversations.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def mock_conversation_payload() -> list[dict]:
    return [
        {
            "id": "conv_1",
            "title": "Planning Session",
            "create_time": 1711000000,
            "update_time": 1711000600,
            "mapping": {
                "node_1": {
                    "id": "node_1",
                    "parent": None,
                    "message": {
                        "id": "msg_1",
                        "author": {"role": "user"},
                        "create_time": 1711000001,
                        "content": {"parts": ["I want to build a persona cockpit."]},
                    },
                },
                "node_2": {
                    "id": "node_2",
                    "parent": "msg_1",
                    "message": {
                        "id": "msg_2",
                        "author": {"role": "assistant"},
                        "create_time": 1711000002,
                        "content": {"parts": ["Start with local imports and simple storage."]},
                    },
                },
            },
        }
    ]


def count_rows(database_path: Path, table_name: str) -> int:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
    return int(row[0])


def test_import_chatgpt_export_from_conversations_json(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    export_dir = tmp_path / "export_dir"
    write_mock_conversations_json(export_dir, mock_conversation_payload())

    summary = import_chatgpt_export(config, export_dir)

    assert summary.conversations_found == 1
    assert summary.messages_imported == 2
    assert summary.duplicate_count == 0
    assert count_rows(config.database_path, "imported_records") == 2
    assert count_rows(config.database_path, "chatgpt_conversations") == 1


def test_import_chatgpt_export_from_zip(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    export_dir = tmp_path / "export_zip_src"
    write_mock_conversations_json(export_dir, mock_conversation_payload())
    archive_path = tmp_path / "chatgpt-export.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(export_dir / "conversations.json", arcname="conversations.json")

    summary = import_chatgpt_export(config, archive_path)

    assert summary.conversations_found == 1
    assert summary.messages_imported == 2
    assert count_rows(config.database_path, "imported_records") == 2


def test_normalize_chatgpt_message_extracts_expected_fields() -> None:
    conversation = mock_conversation_payload()[0]
    node = conversation["mapping"]["node_1"]

    record = normalize_chatgpt_message(
        conversation=conversation,
        node=node,
        source_path="/tmp/export",
        imported_at=utc_now(),
    )

    assert record is not None
    assert record.source_type == "chatgpt_export"
    assert record.metadata["conversation_id"] == "conv_1"
    assert record.metadata["message_id"] == "msg_1"
    assert record.metadata["role"] == "user"
    assert record.content == "I want to build a persona cockpit."


def test_malformed_messages_are_skipped(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    payload = mock_conversation_payload()
    payload[0]["mapping"]["node_3"] = {
        "id": "node_3",
        "parent": "msg_2",
        "message": {
            "id": "msg_3",
            "author": {"role": "assistant"},
            "create_time": 1711000003,
            "content": {"parts": []},
        },
    }
    export_dir = tmp_path / "export_dir"
    write_mock_conversations_json(export_dir, payload)

    summary = import_chatgpt_export(config, export_dir)

    assert summary.messages_imported == 2
    assert summary.skipped_count >= 1


def test_duplicate_chatgpt_messages_are_not_reimported(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    export_dir = tmp_path / "export_dir"
    write_mock_conversations_json(export_dir, mock_conversation_payload())

    first_summary = import_chatgpt_export(config, export_dir)
    second_summary = import_chatgpt_export(config, export_dir)

    assert first_summary.messages_imported == 2
    assert second_summary.messages_imported == 0
    assert second_summary.duplicate_count == 2
    assert count_rows(config.database_path, "imported_records") == 2


def test_empty_export_returns_readable_notice(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    export_dir = tmp_path / "empty_export"
    write_mock_conversations_json(export_dir, [])

    summary = import_chatgpt_export(config, export_dir)

    assert summary.conversations_found == 0
    assert summary.messages_imported == 0
    assert summary.notices

