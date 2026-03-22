from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pop_cockpit.config import AppConfig
from pop_cockpit.schemas import AuditRecord, SessionRecord
from pop_cockpit.storage import (
    get_audit_record,
    get_connection,
    get_session_record,
    insert_audit_record,
    list_audit_records,
)
from pop_cockpit.utils import new_id, sha256_text, write_json


@dataclass(slots=True)
class AuditEnsureResult:
    status: str
    message: str
    audit_record: AuditRecord | None = None


def ensure_audit_record(
    config: AppConfig,
    session_id: str,
    *,
    connection=None,
) -> AuditEnsureResult:
    manage_connection = connection is None
    if connection is None:
        connection = get_connection(config.database_path)

    try:
        existing = get_audit_record(connection, session_id)
        if existing is not None:
            return AuditEnsureResult(
                status="existing",
                message=f"Audit record already exists for session {session_id}.",
                audit_record=existing,
            )

        session = get_session_record(connection, session_id)
        if session is None:
            return AuditEnsureResult(
                status="missing",
                message=f"No session found for {session_id}.",
                audit_record=None,
            )

        audit_record = build_audit_record(config, session)
        write_json(Path(audit_record.artifact_path), audit_record.model_dump(mode="json"))
        Path(audit_record.markdown_path).write_text(
            render_audit_markdown(audit_record),
            encoding="utf-8",
        )
        insert_audit_record(connection, audit_record)
        if manage_connection:
            connection.commit()
        return AuditEnsureResult(
            status="created",
            message=f"Created audit record for session {session_id}.",
            audit_record=audit_record,
        )
    finally:
        if manage_connection:
            connection.close()


def list_audit_entries(
    config: AppConfig,
    *,
    snapshot_scope: str | None = None,
    mode: str | None = None,
    limit: int = 20,
) -> list[AuditRecord]:
    with get_connection(config.database_path) as connection:
        return list_audit_records(
            connection,
            snapshot_scope=snapshot_scope,
            mode=mode,
            limit=limit,
        )


def load_audit_entry(config: AppConfig, session_id: str) -> AuditEnsureResult:
    return ensure_audit_record(config, session_id)


def build_audit_record(config: AppConfig, session: SessionRecord) -> AuditRecord:
    audit_id = new_id("aud")
    artifact_path = config.sessions_dir / f"audit_{session.session_id}.json"
    markdown_path = config.sessions_dir / f"audit_{session.session_id}.md"
    response_hash = sha256_text(session.response) if session.response else None
    return AuditRecord(
        audit_id=audit_id,
        session_id=session.session_id,
        created_at=session.created_at,
        snapshot_scope=session.snapshot_scope,
        mode=session.mode,
        question=session.question,
        persona_core_version_id=session.persona_core_version_id,
        used_snapshot_ids=session.used_snapshot_ids,
        used_memory_ids=session.used_memory_ids,
        used_persona_fields=session.used_persona_fields,
        retrieval_notes=session.retrieval_notes,
        prompt_context_hash=sha256_text(session.prompt_context),
        response_hash=response_hash,
        prompt_context_excerpt=excerpt_text(session.prompt_context, max_chars=320),
        prompt_context_path=session.artifact_path,
        response_present=session.response is not None,
        artifact_path=str(artifact_path),
        markdown_path=str(markdown_path),
    )


def format_audit_list(records: list[AuditRecord]) -> str:
    if not records:
        return "No audit records found."

    header = "session_id                           created_at                   scope                         mode      response"
    separator = "-" * len(header)
    lines = [header, separator]
    for record in records:
        scope = record.snapshot_scope[:28]
        response_flag = "yes" if record.response_present else "no"
        lines.append(
            f"{record.session_id:<36} {record.created_at.isoformat():<28} {scope:<28} {record.mode:<9} {response_flag}"
        )
    return "\n".join(lines)


def format_audit_detail(record: AuditRecord) -> str:
    sections = [
        "# Audit Record",
        "",
        f"- Audit ID: {record.audit_id}",
        f"- Session ID: {record.session_id}",
        f"- Created At: {record.created_at.isoformat()}",
        f"- Scope: {record.snapshot_scope}",
        f"- Mode: {record.mode}",
        f"- Response Present: {'yes' if record.response_present else 'no'}",
        f"- Persona Core Version ID: {record.persona_core_version_id or 'None'}",
        f"- Prompt Context Hash: {record.prompt_context_hash}",
        f"- Response Hash: {record.response_hash or 'None'}",
        f"- Prompt Context Path: {record.prompt_context_path or 'None'}",
        "",
        "## Question",
        record.question,
        "",
        "## Persona Fields",
        ", ".join(record.used_persona_fields) if record.used_persona_fields else "None",
        "",
        "## Snapshot IDs",
        ", ".join(record.used_snapshot_ids) if record.used_snapshot_ids else "None",
        "",
        "## Memory IDs",
        ", ".join(record.used_memory_ids) if record.used_memory_ids else "None",
        "",
        "## Retrieval Notes",
        render_retrieval_notes(record.retrieval_notes),
        "",
        "## Prompt Context Excerpt",
        record.prompt_context_excerpt or "None",
    ]
    return "\n".join(sections).strip() + "\n"


def render_audit_markdown(record: AuditRecord) -> str:
    sections = [
        "# Session Audit",
        "",
        f"- Audit ID: {record.audit_id}",
        f"- Session ID: {record.session_id}",
        f"- Created At: {record.created_at.isoformat()}",
        f"- Scope: {record.snapshot_scope}",
        f"- Mode: {record.mode}",
        f"- Response Present: {'yes' if record.response_present else 'no'}",
        f"- Persona Core Version ID: {record.persona_core_version_id or 'None'}",
        f"- Prompt Context Hash: {record.prompt_context_hash}",
        f"- Response Hash: {record.response_hash or 'None'}",
        f"- Prompt Context Path: {record.prompt_context_path or 'None'}",
        "",
        "## Question",
        record.question,
        "",
        "## Used Snapshot IDs",
        ", ".join(record.used_snapshot_ids) if record.used_snapshot_ids else "None",
        "",
        "## Used Memory IDs",
        ", ".join(record.used_memory_ids) if record.used_memory_ids else "None",
        "",
        "## Used Persona Fields",
        ", ".join(record.used_persona_fields) if record.used_persona_fields else "None",
        "",
        "## Retrieval Notes",
        render_retrieval_notes(record.retrieval_notes),
        "",
        "## Prompt Context Excerpt",
        "```text",
        record.prompt_context_excerpt or "None",
        "```",
    ]
    return "\n".join(sections).strip() + "\n"


def render_retrieval_notes(notes: list[dict]) -> str:
    if not notes:
        return "- No retrieval notes recorded."
    lines = []
    for note in notes:
        lines.append(
            (
                f"- {note['memory_id']}: score={note['score']} reason={note['ranking_reason']} "
                f"event_date={note.get('event_date', 'unknown')}"
            )
        )
    return "\n".join(lines)


def excerpt_text(value: str, *, max_chars: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars].rstrip()}..."


def audit_records_to_json(records: list[AuditRecord]) -> str:
    return json.dumps(
        [record.model_dump(mode="json") for record in records],
        ensure_ascii=False,
        indent=2,
    )


def audit_record_to_json(record: AuditRecord) -> str:
    return json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2)
