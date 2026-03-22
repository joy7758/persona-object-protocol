from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pop_cockpit.config import AppConfig
from pop_cockpit.schemas import (
    AuditRecord,
    ChatGPTConversationMetadata,
    DailyPersonaSnapshot,
    ExecutionIntent,
    ExecutionResult,
    ImportedRecord,
    PersonaCore,
    SessionRecord,
)


def get_connection(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(config: AppConfig) -> None:
    config.ensure_directories()
    with get_connection(config.database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS imported_records (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_path TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                tags_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS daily_persona_snapshots (
                id TEXT PRIMARY KEY,
                date_from TEXT NOT NULL,
                date_to TEXT NOT NULL,
                created_at TEXT NOT NULL,
                snapshot_scope TEXT NOT NULL DEFAULT 'all',
                source_record_ids_json TEXT NOT NULL DEFAULT '[]',
                payload_json TEXT NOT NULL,
                markdown_path TEXT
            );

            CREATE TABLE IF NOT EXISTS chatgpt_conversations (
                conversation_id TEXT PRIMARY KEY,
                conversation_title TEXT NOT NULL DEFAULT '',
                imported_at TEXT NOT NULL,
                source_path TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                first_message_at TEXT,
                last_message_at TEXT,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS persona_core_versions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                snapshot_scope TEXT NOT NULL DEFAULT 'all',
                payload_json TEXT NOT NULL,
                markdown_path TEXT,
                is_current INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                snapshot_scope TEXT NOT NULL DEFAULT 'all',
                persona_core_version_id TEXT,
                used_snapshot_ids_json TEXT NOT NULL DEFAULT '[]',
                used_memory_ids_json TEXT NOT NULL DEFAULT '[]',
                used_persona_fields_json TEXT NOT NULL DEFAULT '[]',
                prompt_context TEXT NOT NULL DEFAULT '',
                response TEXT,
                mode TEXT NOT NULL DEFAULT 'dry_run',
                retrieval_notes_json TEXT NOT NULL DEFAULT '[]',
                source_type_filter TEXT,
                recent_days INTEGER NOT NULL DEFAULT 7,
                artifact_path TEXT NOT NULL DEFAULT '',
                markdown_path TEXT NOT NULL DEFAULT '',
                feedback_status TEXT NOT NULL DEFAULT 'not_reviewed',
                feedback_note TEXT NOT NULL DEFAULT '',
                feedback_updated_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                snapshot_scope TEXT NOT NULL DEFAULT 'all',
                mode TEXT NOT NULL DEFAULT 'dry_run',
                question TEXT NOT NULL DEFAULT '',
                persona_core_version_id TEXT,
                used_snapshot_ids_json TEXT NOT NULL DEFAULT '[]',
                used_memory_ids_json TEXT NOT NULL DEFAULT '[]',
                used_persona_fields_json TEXT NOT NULL DEFAULT '[]',
                retrieval_notes_json TEXT NOT NULL DEFAULT '[]',
                prompt_context_hash TEXT NOT NULL DEFAULT '',
                response_hash TEXT,
                response_present INTEGER NOT NULL DEFAULT 0,
                artifact_path TEXT NOT NULL DEFAULT '',
                markdown_path TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS execution_intents (
                intent_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                source_session_id TEXT,
                source_audit_id TEXT,
                action_type TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_name TEXT NOT NULL,
                parameters_json TEXT NOT NULL DEFAULT '{}',
                rationale TEXT NOT NULL DEFAULT '',
                requires_confirmation INTEGER NOT NULL DEFAULT 1,
                safety_level TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'proposed',
                review_status TEXT NOT NULL DEFAULT 'pending',
                review_note TEXT NOT NULL DEFAULT '',
                review_updated_at TEXT,
                snapshot_scope TEXT NOT NULL DEFAULT 'all',
                persona_core_version_id TEXT,
                intent_key TEXT NOT NULL UNIQUE,
                artifact_path TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS execution_results (
                result_id TEXT PRIMARY KEY,
                intent_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                adapter_type TEXT NOT NULL,
                execution_mode TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 0,
                output_text TEXT NOT NULL DEFAULT '',
                output_data_json TEXT NOT NULL DEFAULT '{}',
                error_text TEXT,
                artifact_path TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL,
                FOREIGN KEY(intent_id) REFERENCES execution_intents(intent_id)
            );
            """
        )
        _ensure_column(
            connection,
            table_name="daily_persona_snapshots",
            column_name="source_record_ids_json",
            column_definition="TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            connection,
            table_name="daily_persona_snapshots",
            column_name="snapshot_scope",
            column_definition="TEXT NOT NULL DEFAULT 'all'",
        )
        _ensure_column(
            connection,
            table_name="imported_records",
            column_name="metadata_json",
            column_definition="TEXT NOT NULL DEFAULT '{}'",
        )
        _ensure_column(
            connection,
            table_name="persona_core_versions",
            column_name="snapshot_scope",
            column_definition="TEXT NOT NULL DEFAULT 'all'",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="snapshot_scope",
            column_definition="TEXT NOT NULL DEFAULT 'all'",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="persona_core_version_id",
            column_definition="TEXT",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="used_snapshot_ids_json",
            column_definition="TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="used_memory_ids_json",
            column_definition="TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="used_persona_fields_json",
            column_definition="TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="mode",
            column_definition="TEXT NOT NULL DEFAULT 'dry_run'",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="retrieval_notes_json",
            column_definition="TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="source_type_filter",
            column_definition="TEXT",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="recent_days",
            column_definition="INTEGER NOT NULL DEFAULT 7",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="artifact_path",
            column_definition="TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="markdown_path",
            column_definition="TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="feedback_status",
            column_definition="TEXT NOT NULL DEFAULT 'not_reviewed'",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="feedback_note",
            column_definition="TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            table_name="sessions",
            column_name="feedback_updated_at",
            column_definition="TEXT",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="snapshot_scope",
            column_definition="TEXT NOT NULL DEFAULT 'all'",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="mode",
            column_definition="TEXT NOT NULL DEFAULT 'dry_run'",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="question",
            column_definition="TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="persona_core_version_id",
            column_definition="TEXT",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="used_snapshot_ids_json",
            column_definition="TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="used_memory_ids_json",
            column_definition="TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="used_persona_fields_json",
            column_definition="TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="retrieval_notes_json",
            column_definition="TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="prompt_context_hash",
            column_definition="TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="response_hash",
            column_definition="TEXT",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="response_present",
            column_definition="INTEGER NOT NULL DEFAULT 0",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="artifact_path",
            column_definition="TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            table_name="audit_logs",
            column_name="markdown_path",
            column_definition="TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="source_session_id",
            column_definition="TEXT",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="source_audit_id",
            column_definition="TEXT",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="parameters_json",
            column_definition="TEXT NOT NULL DEFAULT '{}'",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="rationale",
            column_definition="TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="requires_confirmation",
            column_definition="INTEGER NOT NULL DEFAULT 1",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="safety_level",
            column_definition="TEXT NOT NULL DEFAULT 'medium'",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="status",
            column_definition="TEXT NOT NULL DEFAULT 'proposed'",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="review_status",
            column_definition="TEXT NOT NULL DEFAULT 'pending'",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="review_note",
            column_definition="TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="review_updated_at",
            column_definition="TEXT",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="snapshot_scope",
            column_definition="TEXT NOT NULL DEFAULT 'all'",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="persona_core_version_id",
            column_definition="TEXT",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="intent_key",
            column_definition="TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="artifact_path",
            column_definition="TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            table_name="execution_intents",
            column_name="payload_json",
            column_definition="TEXT NOT NULL DEFAULT '{}'",
        )
        _ensure_column(
            connection,
            table_name="execution_results",
            column_name="artifact_path",
            column_definition="TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            table_name="execution_results",
            column_name="output_data_json",
            column_definition="TEXT NOT NULL DEFAULT '{}'",
        )
        _ensure_column(
            connection,
            table_name="execution_results",
            column_name="payload_json",
            column_definition="TEXT NOT NULL DEFAULT '{}'",
        )


def ensure_runtime(config: AppConfig) -> None:
    initialize_database(config)


def get_imported_record_by_hash(
    connection: sqlite3.Connection, content_hash: str
) -> ImportedRecord | None:
    row = connection.execute(
        """
        SELECT id, source_type, source_path, imported_at, content, content_hash, tags_json
             , metadata_json
        FROM imported_records
        WHERE content_hash = ?
        """,
        (content_hash,),
    ).fetchone()
    if row is None:
        return None

    return ImportedRecord.model_validate(
        {
            "id": row["id"],
            "source_type": row["source_type"],
            "source_path": row["source_path"],
            "imported_at": row["imported_at"],
            "content": row["content"],
            "content_hash": row["content_hash"],
            "tags": json.loads(row["tags_json"]),
            "metadata": json.loads(row["metadata_json"]),
        }
    )


def insert_imported_record(connection: sqlite3.Connection, record: ImportedRecord) -> None:
    connection.execute(
        """
        INSERT INTO imported_records (
            id,
            source_type,
            source_path,
            imported_at,
            content,
            content_hash,
            tags_json,
            metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.id,
            record.source_type,
            record.source_path,
            record.imported_at.isoformat(),
            record.content,
            record.content_hash,
            json.dumps(record.tags, ensure_ascii=False),
            json.dumps(record.metadata, ensure_ascii=False),
        ),
    )


def list_imported_records(
    connection: sqlite3.Connection, source_type: str | None = None
) -> list[ImportedRecord]:
    query = """
        SELECT id, source_type, source_path, imported_at, content, content_hash, tags_json, metadata_json
        FROM imported_records
    """
    parameters: tuple[str, ...] = ()
    if source_type is not None:
        query += " WHERE source_type = ?"
        parameters = (source_type,)
    query += " ORDER BY imported_at ASC, id ASC"
    rows = connection.execute(query, parameters).fetchall()
    return [
        ImportedRecord.model_validate(
            {
                "id": row["id"],
                "source_type": row["source_type"],
                "source_path": row["source_path"],
                "imported_at": row["imported_at"],
                "content": row["content"],
                "content_hash": row["content_hash"],
                "tags": json.loads(row["tags_json"]),
                "metadata": json.loads(row["metadata_json"]),
            }
        )
        for row in rows
    ]


def insert_daily_persona_snapshot(
    connection: sqlite3.Connection,
    snapshot: DailyPersonaSnapshot,
    markdown_path: Path,
    snapshot_scope: str,
) -> None:
    connection.execute(
        """
        INSERT INTO daily_persona_snapshots (
            id,
            date_from,
            date_to,
            created_at,
            snapshot_scope,
            source_record_ids_json,
            payload_json,
            markdown_path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot.id,
            snapshot.date_range.date_from,
            snapshot.date_range.date_to,
            snapshot.created_at.isoformat(),
            snapshot_scope,
            json.dumps(snapshot.source_record_ids, ensure_ascii=False),
            json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False),
            str(markdown_path),
        ),
    )


def find_daily_persona_snapshot(
    connection: sqlite3.Connection,
    date_from: str,
    date_to: str,
    snapshot_scope: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT id, markdown_path, payload_json, created_at
        FROM daily_persona_snapshots
        WHERE date_from = ? AND date_to = ? AND snapshot_scope = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (date_from, date_to, snapshot_scope),
    ).fetchone()


def delete_daily_persona_snapshots(
    connection: sqlite3.Connection,
    date_from: str,
    date_to: str,
    snapshot_scope: str,
) -> int:
    cursor = connection.execute(
        """
        DELETE FROM daily_persona_snapshots
        WHERE date_from = ? AND date_to = ? AND snapshot_scope = ?
        """,
        (date_from, date_to, snapshot_scope),
    )
    return int(cursor.rowcount)


def list_daily_persona_snapshots(
    connection: sqlite3.Connection, snapshot_scope: str = "all"
) -> list[DailyPersonaSnapshot]:
    rows = connection.execute(
        """
        SELECT payload_json
        FROM daily_persona_snapshots
        WHERE snapshot_scope = ?
        ORDER BY date_from ASC, date_to ASC, created_at ASC, id ASC
        """,
        (snapshot_scope,),
    ).fetchall()
    return [
        DailyPersonaSnapshot.model_validate(json.loads(row["payload_json"])) for row in rows
    ]


def insert_persona_core_version(
    connection: sqlite3.Connection,
    version_id: str,
    persona_core: PersonaCore,
    markdown_path: Path,
) -> None:
    connection.execute(
        "UPDATE persona_core_versions SET is_current = 0 WHERE snapshot_scope = ?",
        (persona_core.snapshot_scope,),
    )
    connection.execute(
        """
        INSERT INTO persona_core_versions (
            id,
            created_at,
            snapshot_scope,
            payload_json,
            markdown_path,
            is_current
        )
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (
            version_id,
            persona_core.last_updated.isoformat() if persona_core.last_updated else "",
            persona_core.snapshot_scope,
            json.dumps(persona_core.model_dump(mode="json"), ensure_ascii=False),
            str(markdown_path),
        ),
    )


def get_current_persona_core(
    connection: sqlite3.Connection, snapshot_scope: str = "all"
) -> PersonaCore | None:
    current = get_current_persona_core_version(connection, snapshot_scope=snapshot_scope)
    if current is None:
        return None
    return current[1]


def get_current_persona_core_version(
    connection: sqlite3.Connection, snapshot_scope: str = "all"
) -> tuple[str, PersonaCore] | None:
    row = connection.execute(
        """
        SELECT id, payload_json
        FROM persona_core_versions
        WHERE snapshot_scope = ? AND is_current = 1
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (snapshot_scope,),
    ).fetchone()
    if row is None:
        return None
    return (str(row["id"]), PersonaCore.model_validate(json.loads(row["payload_json"])))


def insert_session_record(connection: sqlite3.Connection, session) -> None:
    connection.execute(
        """
        INSERT INTO sessions (
            session_id,
            question,
            snapshot_scope,
            persona_core_version_id,
            used_snapshot_ids_json,
            used_memory_ids_json,
            used_persona_fields_json,
            prompt_context,
            response,
            mode,
            retrieval_notes_json,
            source_type_filter,
            recent_days,
            artifact_path,
            markdown_path,
            feedback_status,
            feedback_note,
            feedback_updated_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session.session_id,
            session.question,
            session.snapshot_scope,
            session.persona_core_version_id,
            json.dumps(session.used_snapshot_ids, ensure_ascii=False),
            json.dumps(session.used_memory_ids, ensure_ascii=False),
            json.dumps(session.used_persona_fields, ensure_ascii=False),
            session.prompt_context,
            session.response,
            session.mode,
            json.dumps(session.retrieval_notes, ensure_ascii=False),
            session.source_type_filter,
            session.recent_days,
            session.artifact_path,
            session.markdown_path,
            session.feedback_status,
            session.feedback_note,
            session.feedback_updated_at.isoformat() if session.feedback_updated_at else None,
            session.created_at.isoformat(),
        ),
    )


def get_session_record(connection: sqlite3.Connection, session_id: str) -> SessionRecord | None:
    row = connection.execute(
        """
        SELECT
            session_id,
            question,
            snapshot_scope,
            persona_core_version_id,
            used_snapshot_ids_json,
            used_memory_ids_json,
            used_persona_fields_json,
            prompt_context,
            response,
            mode,
            retrieval_notes_json,
            source_type_filter,
            recent_days,
            artifact_path,
            markdown_path,
            feedback_status,
            feedback_note,
            feedback_updated_at,
            created_at
        FROM sessions
        WHERE session_id = ?
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        return None
    return SessionRecord.model_validate(
        {
            "session_id": row["session_id"],
            "question": row["question"],
            "snapshot_scope": row["snapshot_scope"],
            "persona_core_version_id": row["persona_core_version_id"],
            "used_snapshot_ids": json.loads(row["used_snapshot_ids_json"]),
            "used_memory_ids": json.loads(row["used_memory_ids_json"]),
            "used_persona_fields": json.loads(row["used_persona_fields_json"]),
            "prompt_context": row["prompt_context"],
            "response": row["response"],
            "mode": row["mode"],
            "retrieval_notes": json.loads(row["retrieval_notes_json"]),
            "source_type_filter": row["source_type_filter"],
            "recent_days": row["recent_days"],
            "artifact_path": row["artifact_path"],
            "markdown_path": row["markdown_path"],
            "feedback_status": row["feedback_status"],
            "feedback_note": row["feedback_note"],
            "feedback_updated_at": row["feedback_updated_at"],
            "created_at": row["created_at"],
        }
    )


def list_session_records(
    connection: sqlite3.Connection, *, limit: int = 20, snapshot_scope: str | None = None
) -> list[SessionRecord]:
    query = """
        SELECT
            session_id,
            question,
            snapshot_scope,
            persona_core_version_id,
            used_snapshot_ids_json,
            used_memory_ids_json,
            used_persona_fields_json,
            prompt_context,
            response,
            mode,
            retrieval_notes_json,
            source_type_filter,
            recent_days,
            artifact_path,
            markdown_path,
            feedback_status,
            feedback_note,
            feedback_updated_at,
            created_at
        FROM sessions
    """
    parameters: list[str | int] = []
    if snapshot_scope is not None:
        query += " WHERE snapshot_scope = ?"
        parameters.append(snapshot_scope)
    query += " ORDER BY created_at DESC, session_id DESC LIMIT ?"
    parameters.append(limit)
    rows = connection.execute(query, tuple(parameters)).fetchall()
    return [
        SessionRecord.model_validate(
            {
                "session_id": row["session_id"],
                "question": row["question"],
                "snapshot_scope": row["snapshot_scope"],
                "persona_core_version_id": row["persona_core_version_id"],
                "used_snapshot_ids": json.loads(row["used_snapshot_ids_json"]),
                "used_memory_ids": json.loads(row["used_memory_ids_json"]),
                "used_persona_fields": json.loads(row["used_persona_fields_json"]),
                "prompt_context": row["prompt_context"],
                "response": row["response"],
                "mode": row["mode"],
                "retrieval_notes": json.loads(row["retrieval_notes_json"]),
                "source_type_filter": row["source_type_filter"],
                "recent_days": row["recent_days"],
                "artifact_path": row["artifact_path"],
                "markdown_path": row["markdown_path"],
                "feedback_status": row["feedback_status"],
                "feedback_note": row["feedback_note"],
                "feedback_updated_at": row["feedback_updated_at"],
                "created_at": row["created_at"],
            }
        )
        for row in rows
    ]


def update_session_feedback(
    connection: sqlite3.Connection,
    session_id: str,
    *,
    feedback_status: str,
    feedback_note: str,
    feedback_updated_at: str,
) -> int:
    cursor = connection.execute(
        """
        UPDATE sessions
        SET
            feedback_status = ?,
            feedback_note = ?,
            feedback_updated_at = ?
        WHERE session_id = ?
        """,
        (feedback_status, feedback_note, feedback_updated_at, session_id),
    )
    return int(cursor.rowcount)


def get_audit_record(connection: sqlite3.Connection, session_id: str) -> AuditRecord | None:
    row = connection.execute(
        """
        SELECT payload_json
        FROM audit_logs
        WHERE session_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        return None
    return AuditRecord.model_validate(json.loads(row["payload_json"]))


def list_audit_records(
    connection: sqlite3.Connection,
    *,
    snapshot_scope: str | None = None,
    mode: str | None = None,
    limit: int = 20,
) -> list[AuditRecord]:
    query = """
        SELECT payload_json
        FROM audit_logs
    """
    clauses: list[str] = []
    parameters: list[str | int] = []
    if snapshot_scope is not None:
        clauses.append("snapshot_scope = ?")
        parameters.append(snapshot_scope)
    if mode is not None:
        clauses.append("mode = ?")
        parameters.append(mode)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC, id DESC LIMIT ?"
    parameters.append(limit)
    rows = connection.execute(query, tuple(parameters)).fetchall()
    return [AuditRecord.model_validate(json.loads(row["payload_json"])) for row in rows]


def insert_audit_record(connection: sqlite3.Connection, audit_record: AuditRecord) -> None:
    connection.execute(
        """
        INSERT INTO audit_logs (
            id,
            session_id,
            created_at,
            snapshot_scope,
            mode,
            question,
            persona_core_version_id,
            used_snapshot_ids_json,
            used_memory_ids_json,
            used_persona_fields_json,
            retrieval_notes_json,
            prompt_context_hash,
            response_hash,
            response_present,
            artifact_path,
            markdown_path,
            payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            audit_record.audit_id,
            audit_record.session_id,
            audit_record.created_at.isoformat(),
            audit_record.snapshot_scope,
            audit_record.mode,
            audit_record.question,
            audit_record.persona_core_version_id,
            json.dumps(audit_record.used_snapshot_ids, ensure_ascii=False),
            json.dumps(audit_record.used_memory_ids, ensure_ascii=False),
            json.dumps(audit_record.used_persona_fields, ensure_ascii=False),
            json.dumps(audit_record.retrieval_notes, ensure_ascii=False),
            audit_record.prompt_context_hash,
            audit_record.response_hash,
            1 if audit_record.response_present else 0,
            audit_record.artifact_path,
            audit_record.markdown_path,
            json.dumps(audit_record.model_dump(mode="json"), ensure_ascii=False),
        ),
    )


def list_available_snapshot_scopes(connection: sqlite3.Connection) -> list[str]:
    scopes = {"all"}
    for table_name in (
        "daily_persona_snapshots",
        "persona_core_versions",
        "sessions",
        "audit_logs",
        "execution_intents",
    ):
        try:
            rows = connection.execute(f"SELECT DISTINCT snapshot_scope FROM {table_name}").fetchall()
        except sqlite3.OperationalError:
            continue
        for row in rows:
            scope = row["snapshot_scope"]
            if scope:
                scopes.add(str(scope))
    return sorted(scopes)


def upsert_chatgpt_conversation(
    connection: sqlite3.Connection, conversation: ChatGPTConversationMetadata
) -> None:
    connection.execute(
        """
        INSERT INTO chatgpt_conversations (
            conversation_id,
            conversation_title,
            imported_at,
            source_path,
            message_count,
            first_message_at,
            last_message_at,
            payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(conversation_id) DO UPDATE SET
            conversation_title = excluded.conversation_title,
            imported_at = excluded.imported_at,
            source_path = excluded.source_path,
            message_count = excluded.message_count,
            first_message_at = excluded.first_message_at,
            last_message_at = excluded.last_message_at,
            payload_json = excluded.payload_json
        """,
        (
            conversation.conversation_id,
            conversation.conversation_title,
            conversation.imported_at.isoformat(),
            conversation.source_path,
            conversation.message_count,
            conversation.first_message_at,
            conversation.last_message_at,
            json.dumps(conversation.model_dump(mode="json"), ensure_ascii=False),
        ),
    )


def get_execution_intent(connection: sqlite3.Connection, intent_id: str) -> ExecutionIntent | None:
    row = connection.execute(
        """
        SELECT payload_json
        FROM execution_intents
        WHERE intent_id = ?
        """,
        (intent_id,),
    ).fetchone()
    if row is None:
        return None
    return ExecutionIntent.model_validate(json.loads(row["payload_json"]))


def find_execution_intent_by_key(
    connection: sqlite3.Connection, intent_key: str
) -> ExecutionIntent | None:
    row = connection.execute(
        """
        SELECT payload_json
        FROM execution_intents
        WHERE intent_key = ? AND status NOT IN ('rejected', 'failed')
        ORDER BY created_at DESC, intent_id DESC
        LIMIT 1
        """,
        (intent_key,),
    ).fetchone()
    if row is None:
        return None
    return ExecutionIntent.model_validate(json.loads(row["payload_json"]))


def list_execution_intents(
    connection: sqlite3.Connection, *, limit: int = 20
) -> list[ExecutionIntent]:
    rows = connection.execute(
        """
        SELECT payload_json
        FROM execution_intents
        ORDER BY created_at DESC, intent_id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [ExecutionIntent.model_validate(json.loads(row["payload_json"])) for row in rows]


def insert_execution_intent(
    connection: sqlite3.Connection,
    intent: ExecutionIntent,
    *,
    intent_key: str,
    artifact_path: Path,
) -> None:
    connection.execute(
        """
        INSERT INTO execution_intents (
            intent_id,
            created_at,
            source_session_id,
            source_audit_id,
            action_type,
            target_type,
            target_name,
            parameters_json,
            rationale,
            requires_confirmation,
            safety_level,
            status,
            review_status,
            review_note,
            review_updated_at,
            snapshot_scope,
            persona_core_version_id,
            intent_key,
            artifact_path,
            payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            intent.intent_id,
            intent.created_at.isoformat(),
            intent.source_session_id,
            intent.source_audit_id,
            intent.action_type,
            intent.target_type,
            intent.target_name,
            json.dumps(intent.parameters, ensure_ascii=False),
            intent.rationale,
            1 if intent.requires_confirmation else 0,
            intent.safety_level,
            intent.status,
            intent.review_status,
            intent.review_note,
            intent.review_updated_at.isoformat() if intent.review_updated_at else None,
            intent.snapshot_scope,
            intent.persona_core_version_id,
            intent_key,
            str(artifact_path),
            json.dumps(intent.model_dump(mode="json"), ensure_ascii=False),
        ),
    )


def update_execution_intent(
    connection: sqlite3.Connection,
    intent: ExecutionIntent,
    *,
    artifact_path: Path,
) -> None:
    connection.execute(
        """
        UPDATE execution_intents
        SET
            source_session_id = ?,
            source_audit_id = ?,
            action_type = ?,
            target_type = ?,
            target_name = ?,
            parameters_json = ?,
            rationale = ?,
            requires_confirmation = ?,
            safety_level = ?,
            status = ?,
            review_status = ?,
            review_note = ?,
            review_updated_at = ?,
            snapshot_scope = ?,
            persona_core_version_id = ?,
            artifact_path = ?,
            payload_json = ?
        WHERE intent_id = ?
        """,
        (
            intent.source_session_id,
            intent.source_audit_id,
            intent.action_type,
            intent.target_type,
            intent.target_name,
            json.dumps(intent.parameters, ensure_ascii=False),
            intent.rationale,
            1 if intent.requires_confirmation else 0,
            intent.safety_level,
            intent.status,
            intent.review_status,
            intent.review_note,
            intent.review_updated_at.isoformat() if intent.review_updated_at else None,
            intent.snapshot_scope,
            intent.persona_core_version_id,
            str(artifact_path),
            json.dumps(intent.model_dump(mode="json"), ensure_ascii=False),
            intent.intent_id,
        ),
    )


def update_execution_review(
    connection: sqlite3.Connection,
    intent_id: str,
    *,
    review_status: str,
    review_note: str,
    review_updated_at: str,
) -> int:
    cursor = connection.execute(
        """
        UPDATE execution_intents
        SET
            review_status = ?,
            review_note = ?,
            review_updated_at = ?
        WHERE intent_id = ?
        """,
        (review_status, review_note, review_updated_at, intent_id),
    )
    return int(cursor.rowcount)


def list_execution_results(
    connection: sqlite3.Connection,
    *,
    limit: int = 20,
    intent_id: str | None = None,
) -> list[ExecutionResult]:
    query = """
        SELECT payload_json
        FROM execution_results
    """
    parameters: list[str | int] = []
    if intent_id is not None:
        query += " WHERE intent_id = ?"
        parameters.append(intent_id)
    query += " ORDER BY created_at DESC, result_id DESC LIMIT ?"
    parameters.append(limit)
    rows = connection.execute(query, tuple(parameters)).fetchall()
    return [ExecutionResult.model_validate(json.loads(row["payload_json"])) for row in rows]


def insert_execution_result(
    connection: sqlite3.Connection,
    result: ExecutionResult,
    *,
    artifact_path: Path,
) -> None:
    connection.execute(
        """
        INSERT INTO execution_results (
            result_id,
            intent_id,
            created_at,
            adapter_type,
            execution_mode,
            success,
            output_text,
            output_data_json,
            error_text,
            artifact_path,
            payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.result_id,
            result.intent_id,
            result.created_at.isoformat(),
            result.adapter_type,
            result.execution_mode,
            1 if result.success else 0,
            result.output_text,
            json.dumps(result.output_data, ensure_ascii=False),
            result.error_text,
            str(artifact_path),
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False),
        ),
    )


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name in columns:
        return
    try:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise
