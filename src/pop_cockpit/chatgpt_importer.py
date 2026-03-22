from __future__ import annotations

import json
import tempfile
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterator

from pop_cockpit.config import AppConfig
from pop_cockpit.schemas import ChatGPTConversationMetadata, ImportedRecord
from pop_cockpit.storage import (
    get_connection,
    get_imported_record_by_hash,
    insert_imported_record,
    upsert_chatgpt_conversation,
)
from pop_cockpit.utils import new_id, sha256_text, utc_now, write_json


@dataclass(slots=True)
class ChatGPTImportSummary:
    target_path: Path
    conversations_found: int = 0
    messages_imported: int = 0
    duplicate_count: int = 0
    skipped_count: int = 0
    imported_records: list[ImportedRecord] = field(default_factory=list)
    conversations: list[ChatGPTConversationMetadata] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)


def import_chatgpt_export(config: AppConfig, path: Path) -> ChatGPTImportSummary:
    target_path = path.expanduser().resolve()
    if not target_path.exists():
        raise FileNotFoundError(f"Path not found: {target_path}")

    summary = ChatGPTImportSummary(target_path=target_path)
    with _prepare_export_workspace(target_path) as export_root:
        conversations_file = _find_export_entry(export_root, "conversations.json")
        chat_html_file = _find_export_entry(export_root, "chat.html")

        with get_connection(config.database_path) as connection:
            if conversations_file is not None:
                _import_conversations_json(
                    connection=connection,
                    config=config,
                    summary=summary,
                    conversations_file=conversations_file,
                    source_path=str(target_path),
                )
                return summary

            if chat_html_file is not None:
                summary.notices.append(
                    "conversations.json not found; using chat.html fallback."
                )
                _import_chat_html_fallback(
                    connection=connection,
                    config=config,
                    summary=summary,
                    chat_html_file=chat_html_file,
                    source_path=str(target_path),
                )
                return summary

    summary.notices.append("No conversations.json or chat.html found in export.")
    return summary


def format_chatgpt_import_summary(summary: ChatGPTImportSummary) -> str:
    lines = [
        "ChatGPT export import summary",
        f"target: {summary.target_path}",
        f"conversations found: {summary.conversations_found}",
        f"messages imported: {summary.messages_imported}",
        f"duplicates: {summary.duplicate_count}",
        f"skipped: {summary.skipped_count}",
    ]
    for notice in summary.notices:
        lines.append(f"- notice: {notice}")
    return "\n".join(lines)


def normalize_chatgpt_message(
    *,
    conversation: dict[str, Any],
    node: dict[str, Any],
    source_path: str,
    imported_at,
) -> ImportedRecord | None:
    message = node.get("message")
    if not isinstance(message, dict):
        return None

    content = _extract_message_content(message)
    if not content:
        return None

    conversation_id = _conversation_id(conversation)
    conversation_title = str(conversation.get("title") or "Untitled conversation")
    message_id = str(message.get("id") or node.get("id") or "")
    if not message_id:
        return None

    role = _message_role(message)
    created_at = _timestamp_to_iso(message.get("create_time"))
    parent_message_id = node.get("parent")
    content_hash = sha256_text(
        json.dumps(
            {
                "source_type": "chatgpt_export",
                "conversation_id": conversation_id,
                "message_id": message_id,
                "role": role,
                "content": content,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return ImportedRecord(
        id=new_id("imp"),
        source_type="chatgpt_export",
        source_path=source_path,
        imported_at=imported_at,
        content=content,
        content_hash=content_hash,
        tags=["chatgpt_export", f"role:{role}"],
        metadata={
            "conversation_id": conversation_id,
            "conversation_title": conversation_title,
            "message_id": message_id,
            "parent_message_id": parent_message_id,
            "role": role,
            "created_at": created_at,
            "source_entry": "conversations.json",
        },
    )


@contextmanager
def _prepare_export_workspace(path: Path) -> Iterator[Path]:
    if path.is_dir():
        yield path
        return
    if path.is_file() and path.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory(prefix="pop_chatgpt_export_") as temp_dir:
            with zipfile.ZipFile(path) as archive:
                archive.extractall(temp_dir)
            yield Path(temp_dir)
        return
    raise ValueError(f"Unsupported export input: {path}")


def _find_export_entry(root: Path, name: str) -> Path | None:
    matches = sorted(root.rglob(name))
    return matches[0] if matches else None


def _import_conversations_json(
    *,
    connection,
    config: AppConfig,
    summary: ChatGPTImportSummary,
    conversations_file: Path,
    source_path: str,
) -> None:
    payload = json.loads(conversations_file.read_text(encoding="utf-8"))
    conversations = _coerce_conversations_payload(payload)
    summary.conversations_found = len(conversations)
    if not conversations:
        summary.notices.append("conversations.json was found but contained no conversations.")
        return

    imported_at = utc_now()
    for conversation in conversations:
        if not isinstance(conversation, dict):
            summary.skipped_count += 1
            summary.notices.append("Skipped malformed conversation entry in conversations.json.")
            continue

        metadata, records, skipped_messages = _parse_conversation(
            conversation=conversation,
            source_path=source_path,
            imported_at=imported_at,
        )
        summary.skipped_count += skipped_messages
        summary.conversations.append(metadata)
        upsert_chatgpt_conversation(connection, metadata)
        _write_conversation_copy(config, metadata)

        for record in records:
            if _persist_record(connection, config, record):
                summary.messages_imported += 1
                summary.imported_records.append(record)
            else:
                summary.duplicate_count += 1


def _import_chat_html_fallback(
    *,
    connection,
    config: AppConfig,
    summary: ChatGPTImportSummary,
    chat_html_file: Path,
    source_path: str,
) -> None:
    imported_at = utc_now()
    parser = _ChatExportHTMLParser()
    parser.feed(chat_html_file.read_text(encoding="utf-8", errors="replace"))
    content = parser.text_content()
    if not content:
        summary.notices.append("chat.html fallback found no readable text.")
        summary.skipped_count += 1
        return

    conversation_id = f"chat_html_{sha256_text(source_path)[:16]}"
    title = parser.title.strip() or "ChatGPT HTML Export"
    metadata = ChatGPTConversationMetadata(
        conversation_id=conversation_id,
        conversation_title=title,
        source_path=source_path,
        imported_at=imported_at,
        message_count=1,
        message_ids=[f"{conversation_id}_html"],
        metadata={"source_entry": "chat.html", "fallback": True},
    )
    record = ImportedRecord(
        id=new_id("imp"),
        source_type="chatgpt_export",
        source_path=source_path,
        imported_at=imported_at,
        content=content,
        content_hash=sha256_text(
            json.dumps(
                {
                    "source_type": "chatgpt_export",
                    "conversation_id": conversation_id,
                    "message_id": f"{conversation_id}_html",
                    "role": "unknown",
                    "content": content,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        ),
        tags=["chatgpt_export", "fallback", "role:unknown"],
        metadata={
            "conversation_id": conversation_id,
            "conversation_title": title,
            "message_id": f"{conversation_id}_html",
            "parent_message_id": None,
            "role": "unknown",
            "created_at": None,
            "source_entry": "chat.html",
            "fallback": True,
        },
    )

    summary.conversations_found = 1
    summary.conversations.append(metadata)
    upsert_chatgpt_conversation(connection, metadata)
    _write_conversation_copy(config, metadata)
    if _persist_record(connection, config, record):
        summary.messages_imported = 1
        summary.imported_records.append(record)
    else:
        summary.duplicate_count = 1


def _coerce_conversations_payload(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        conversations = payload.get("conversations")
        if isinstance(conversations, list):
            return conversations
    return []


def _parse_conversation(
    *,
    conversation: dict[str, Any],
    source_path: str,
    imported_at,
) -> tuple[ChatGPTConversationMetadata, list[ImportedRecord], int]:
    mapping = conversation.get("mapping")
    if not isinstance(mapping, dict):
        mapping = {}

    records: list[ImportedRecord] = []
    skipped_messages = 0
    sortable_nodes = sorted(
        mapping.values(),
        key=lambda node: _node_sort_key(node),
    )
    for node in sortable_nodes:
        if not isinstance(node, dict):
            skipped_messages += 1
            continue
        record = normalize_chatgpt_message(
            conversation=conversation,
            node=node,
            source_path=source_path,
            imported_at=imported_at,
        )
        if record is None:
            skipped_messages += 1
            continue
        records.append(record)

    created_times = [
        record.metadata["created_at"]
        for record in records
        if record.metadata.get("created_at") is not None
    ]
    metadata = ChatGPTConversationMetadata(
        conversation_id=_conversation_id(conversation),
        conversation_title=str(conversation.get("title") or "Untitled conversation"),
        source_path=source_path,
        imported_at=imported_at,
        message_count=len(records),
        message_ids=[str(record.metadata["message_id"]) for record in records],
        first_message_at=min(created_times) if created_times else None,
        last_message_at=max(created_times) if created_times else None,
        metadata={
            "source_entry": "conversations.json",
            "conversation_create_time": _timestamp_to_iso(conversation.get("create_time")),
            "conversation_update_time": _timestamp_to_iso(conversation.get("update_time")),
        },
    )
    return metadata, records, skipped_messages


def _persist_record(connection, config: AppConfig, record: ImportedRecord) -> bool:
    existing = get_imported_record_by_hash(connection, record.content_hash)
    if existing is not None:
        return False
    insert_imported_record(connection, record)
    write_json(config.raw_logs_dir / f"{record.id}.json", record.model_dump(mode="json"))
    return True


def _write_conversation_copy(config: AppConfig, metadata: ChatGPTConversationMetadata) -> None:
    conversation_key = metadata.conversation_id.replace("/", "_")
    write_json(
        config.raw_logs_dir / f"chatgpt_conversation_{conversation_key}.json",
        metadata.model_dump(mode="json"),
    )


def _conversation_id(conversation: dict[str, Any]) -> str:
    value = conversation.get("id") or conversation.get("conversation_id")
    if value:
        return str(value)
    return f"conversation_{sha256_text(json.dumps(conversation, sort_keys=True))[:16]}"


def _message_role(message: dict[str, Any]) -> str:
    author = message.get("author")
    if isinstance(author, dict) and author.get("role"):
        return str(author["role"])
    if message.get("role"):
        return str(message["role"])
    return "unknown"


def _extract_message_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, dict):
        if isinstance(content.get("parts"), list):
            parts = [_normalize_content_part(part) for part in content["parts"]]
            joined = "\n".join(part for part in parts if part)
            return joined.strip()
        if isinstance(content.get("text"), str):
            return content["text"].strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def _normalize_content_part(part: Any) -> str:
    if isinstance(part, str):
        return part.strip()
    if isinstance(part, dict):
        if isinstance(part.get("text"), str):
            return part["text"].strip()
        return json.dumps(part, ensure_ascii=False, sort_keys=True)
    return str(part).strip()


def _timestamp_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).isoformat()
    if isinstance(value, str):
        return value
    return str(value)


def _node_sort_key(node: Any) -> tuple[int, Any, str]:
    if not isinstance(node, dict):
        return (1, "", "")
    message = node.get("message")
    if isinstance(message, dict):
        created_at = message.get("create_time")
        if created_at is not None:
            return (0, created_at, str(message.get("id") or node.get("id") or ""))
    return (1, str(node.get("id") or ""), "")


class _ChatExportHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.title = ""
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title += text
            return
        self._chunks.append(text)

    def text_content(self) -> str:
        seen: list[str] = []
        for chunk in self._chunks:
            if not seen or seen[-1] != chunk:
                seen.append(chunk)
        return "\n".join(seen).strip()
