from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from pop_cockpit.config import AppConfig
from pop_cockpit.execution import write_execution_intent_artifact
from pop_cockpit.extractor import write_daily_snapshot_files
from pop_cockpit.injector import render_session_markdown
from pop_cockpit.persona import write_persona_core_files
from pop_cockpit.schemas import DailyPersonaSnapshot, PersonaCore, ProjectSettings
from pop_cockpit.settings import load_project_settings, save_project_settings
from pop_cockpit.storage import (
    delete_daily_persona_snapshots,
    find_daily_persona_snapshot,
    get_connection,
    get_current_persona_core,
    get_current_persona_core_version,
    get_execution_intent,
    get_session_record,
    insert_daily_persona_snapshot,
    insert_persona_core_version,
    list_daily_persona_snapshots,
    update_execution_intent,
    update_session_feedback,
)
from pop_cockpit.utils import new_id, utc_now, write_json

SYNC_PROVIDER = "google_drive_folder"
EVENT_PACKAGE_VERSION = 1
PERSONA_PACKAGE_VERSION = 1
SYNC_KDF_SALT = b"pop-sync-helper-mini:fernet-key:v1"


@dataclass(slots=True)
class SyncActionResult:
    status: str
    message: str
    payload: dict[str, Any] | None = None


@dataclass(slots=True)
class SyncStatusSummary:
    enabled: bool
    provider: str
    device_id: str
    device_name: str
    device_role: str
    sync_root_path: str
    sync_passphrase_set: bool
    sync_auto_start: bool
    sync_interval_seconds: int
    last_sync_time: str
    pending_outgoing_count: int
    pending_incoming_count: int
    last_error: str
    conflict_count: int
    recent_history: list[dict[str, Any]]
    health: str
    warnings: list[str]


@dataclass(slots=True)
class SyncWorkerHandle:
    thread: threading.Thread
    stop_event: threading.Event


def ensure_device_identity(config: AppConfig) -> ProjectSettings:
    settings = load_project_settings(config)
    changed = False
    if not settings.device_id:
        settings.device_id = new_id("dev")
        changed = True
    if not settings.device_name:
        settings.device_name = platform.node() or settings.device_id
        changed = True
    if changed:
        save_project_settings(config, settings)
    return settings


def initialize_sync(
    config: AppConfig,
    *,
    root_path: str,
    role: str,
    device_name: str,
    provider: str = SYNC_PROVIDER,
) -> SyncActionResult:
    if provider != SYNC_PROVIDER:
        return SyncActionResult(status="error", message="Only google_drive_folder sync is supported.")
    if role not in {"primary", "secondary"}:
        return SyncActionResult(status="error", message="Device role must be primary or secondary.")
    if not root_path.strip():
        return SyncActionResult(status="error", message="Sync root path cannot be empty.")
    settings = ensure_device_identity(config)
    settings.sync_provider = provider
    settings.sync_root_path = root_path.strip()
    settings.device_role = role
    settings.device_name = device_name.strip() or settings.device_name
    settings.sync_enabled = True
    settings.sync_auto_start = True
    save_project_settings(config, settings)
    sync_root = _require_sync_root(settings)
    try:
        _ensure_sync_root_structure(sync_root)
    except OSError:
        return SyncActionResult(
            status="error",
            message="Sync root is not accessible. Check the Google Drive folder path first.",
        )
    _write_device_manifest(sync_root, settings)
    append_sync_history(
        config,
        action="init",
        status="configured",
        message="Sync root configured.",
        details={"sync_root_path": settings.sync_root_path, "device_role": settings.device_role},
    )
    return SyncActionResult(
        status="configured",
        message=f"Sync is ready for {settings.device_name} ({settings.device_role}).",
        payload={"device_id": settings.device_id, "sync_root_path": settings.sync_root_path},
    )


def pause_sync(config: AppConfig) -> SyncActionResult:
    settings = load_project_settings(config)
    settings.sync_enabled = False
    save_project_settings(config, settings)
    append_sync_history(config, action="pause", status="paused", message="Sync paused.")
    return SyncActionResult(status="paused", message="Sync paused.")


def resume_sync(config: AppConfig) -> SyncActionResult:
    settings = ensure_device_identity(config)
    settings.sync_enabled = True
    save_project_settings(config, settings)
    append_sync_history(config, action="resume", status="active", message="Sync resumed.")
    return SyncActionResult(status="active", message="Sync resumed.")


def set_sync_passphrase(config: AppConfig, passphrase: str) -> SyncActionResult:
    trimmed = passphrase.strip()
    if not trimmed:
        return SyncActionResult(status="error", message="Sync passphrase cannot be empty.")
    key_b64 = _derive_local_sync_key(trimmed).decode("ascii")
    payload = {
        "key_b64": key_b64,
        "saved_at": utc_now().isoformat(),
        "version": 1,
    }
    config.sync_secret_path.parent.mkdir(parents=True, exist_ok=True)
    config.sync_secret_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(config.sync_secret_path, 0o600)
    except OSError:
        pass
    settings = load_project_settings(config)
    settings.sync_passphrase_set = True
    save_project_settings(config, settings)
    append_sync_history(
        config,
        action="set_passphrase",
        status="saved",
        message="Sync passphrase saved locally.",
    )
    return SyncActionResult(status="saved", message="Sync passphrase saved locally.")


def export_new_event_package(config: AppConfig) -> SyncActionResult:
    settings = ensure_device_identity(config)
    validation_error = _validate_sync_configuration(config, settings, require_passphrase=True)
    if validation_error is not None:
        return validation_error
    sync_root = _require_sync_root(settings)
    _ensure_sync_root_structure(sync_root)
    _write_device_manifest(sync_root, settings)

    state = _load_sync_state(config)
    events = _collect_pending_events(config, since=state.get("last_event_export_at", ""))
    if not events:
        return SyncActionResult(status="noop", message="No new feedback events to export.", payload={"event_count": 0})

    sequence = int(state.get("last_event_sequence", 0)) + 1
    package_id = f"evt_{settings.device_id}_{sequence:06d}"
    today_folder = sync_root / "events" / utc_now().date().isoformat()
    today_folder.mkdir(parents=True, exist_ok=True)
    encrypted_path = today_folder / f"{settings.device_id}-{sequence:06d}.jsonl.enc"
    metadata_path = today_folder / f"{settings.device_id}-{sequence:06d}.meta.json"

    payload_text = "\n".join(json.dumps(event, ensure_ascii=False, separators=(",", ":")) for event in events)
    encrypted = _encrypt_payload(config, payload_text.encode("utf-8"))
    encrypted_path.write_bytes(encrypted["ciphertext"])
    metadata = {
        "package_id": package_id,
        "package_type": "event",
        "package_version": EVENT_PACKAGE_VERSION,
        "created_at": utc_now().isoformat(),
        "payload_format": "jsonl",
        "event_count": len(events),
        "event_types": sorted({event["event_type"] for event in events}),
        "source_device_id": settings.device_id,
        "source_device_name": settings.device_name,
        "source_device_role": settings.device_role,
        "provider": settings.sync_provider,
        "encrypted_file": _relative_to_root(sync_root, encrypted_path),
        "encryption": encrypted["metadata"],
    }
    write_json(metadata_path, metadata)

    state["last_event_sequence"] = sequence
    state["last_event_export_at"] = max(event["updated_at"] for event in events)
    _save_sync_state(config, state)
    append_sync_history(
        config,
        action="export_events",
        status="exported",
        message=f"Exported {len(events)} event updates.",
        details={"package_id": package_id, "metadata_path": str(metadata_path)},
    )
    return SyncActionResult(
        status="exported",
        message=f"Exported {len(events)} event updates.",
        payload={"package_id": package_id, "metadata_path": str(metadata_path), "event_count": len(events)},
    )


def export_persona_sync_package(config: AppConfig, *, force: bool = False) -> SyncActionResult:
    settings = ensure_device_identity(config)
    if settings.device_role != "primary":
        return SyncActionResult(
            status="skipped",
            message="Only the primary device exports persona packages by default.",
        )
    validation_error = _validate_sync_configuration(config, settings, require_passphrase=True)
    if validation_error is not None:
        return validation_error
    sync_root = _require_sync_root(settings)
    _ensure_sync_root_structure(sync_root)
    _write_device_manifest(sync_root, settings)

    with get_connection(config.database_path) as connection:
        persona_core = get_current_persona_core(connection, snapshot_scope="all")
        persona_version = get_current_persona_core_version(connection, snapshot_scope="all")
        snapshots = list_daily_persona_snapshots(connection, snapshot_scope="all")
    if persona_core is None or persona_version is None:
        return SyncActionResult(status="empty", message="No persona core is available to export yet.")

    state = _load_sync_state(config)
    last_exported_persona_at = state.get("last_persona_exported_at", "")
    persona_updated_at = persona_core.last_updated.isoformat() if persona_core.last_updated else ""
    if not force and last_exported_persona_at and persona_updated_at and persona_updated_at <= last_exported_persona_at:
        return SyncActionResult(status="noop", message="Persona package is already up to date.")

    recent_snapshots = _recent_snapshots(snapshots, days=settings.sync_snapshot_days)
    package_id = new_id("prs")
    created_at = utc_now()
    history_stem = f"{created_at.strftime('%Y%m%dT%H%M%SZ')}_{settings.device_id}_{package_id}"
    history_dir = sync_root / "packages" / "persona" / "history"
    latest_dir = sync_root / "packages" / "persona" / "latest"
    history_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)
    history_encrypted = history_dir / f"{history_stem}.enc"
    history_metadata = history_dir / f"{history_stem}.meta.json"
    latest_encrypted = latest_dir / f"{settings.device_id}.enc"
    latest_metadata = latest_dir / f"{settings.device_id}.meta.json"

    payload = {
        "kind": "persona_package",
        "package_version": PERSONA_PACKAGE_VERSION,
        "created_at": created_at.isoformat(),
        "source_device": {
            "device_id": settings.device_id,
            "device_name": settings.device_name,
            "device_role": settings.device_role,
        },
        "snapshot_scope": "all",
        "snapshot_limit_days": settings.sync_snapshot_days,
        "persona_version_id": persona_version[0],
        "persona_core": persona_core.model_dump(mode="json"),
        "daily_snapshots": [snapshot.model_dump(mode="json") for snapshot in recent_snapshots],
        "metadata": {
            "daily_snapshot_count": len(recent_snapshots),
            "persona_source_snapshot_count": len(persona_core.source_snapshot_ids),
        },
    }
    encrypted = _encrypt_payload(
        config,
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
    )
    history_encrypted.write_bytes(encrypted["ciphertext"])
    latest_encrypted.write_bytes(encrypted["ciphertext"])
    metadata = {
        "package_id": package_id,
        "package_type": "persona",
        "package_version": PERSONA_PACKAGE_VERSION,
        "created_at": created_at.isoformat(),
        "payload_format": "json",
        "source_device_id": settings.device_id,
        "source_device_name": settings.device_name,
        "source_device_role": settings.device_role,
        "provider": settings.sync_provider,
        "snapshot_scope": "all",
        "persona_version_id": persona_version[0],
        "persona_last_updated": persona_updated_at,
        "snapshot_count": len(recent_snapshots),
        "encrypted_file": _relative_to_root(sync_root, history_encrypted),
        "latest_encrypted_file": _relative_to_root(sync_root, latest_encrypted),
        "encryption": encrypted["metadata"],
    }
    write_json(history_metadata, metadata)
    write_json(latest_metadata, metadata)
    write_json(sync_root / "versions" / f"{package_id}.json", metadata)

    state["last_persona_exported_at"] = persona_updated_at
    _save_sync_state(config, state)
    append_sync_history(
        config,
        action="export_persona",
        status="exported",
        message="Exported latest persona package.",
        details={"package_id": package_id, "metadata_path": str(history_metadata)},
    )
    return SyncActionResult(
        status="exported",
        message="Exported latest persona package.",
        payload={"package_id": package_id, "metadata_path": str(history_metadata)},
    )


def import_remote_packages(config: AppConfig) -> SyncActionResult:
    settings = ensure_device_identity(config)
    validation_error = _validate_sync_configuration(config, settings, require_passphrase=True)
    if validation_error is not None:
        return validation_error
    sync_root = _require_sync_root(settings)
    _ensure_sync_root_structure(sync_root)

    imported = 0
    conflicts = 0
    skipped = 0
    for metadata_path, metadata in _iter_pending_remote_package_metadata(sync_root, settings):
        try:
            if metadata["package_type"] == "event":
                result = _import_event_package(config, sync_root, settings, metadata)
            else:
                result = _import_persona_package(config, sync_root, settings, metadata)
        except InvalidToken as exc:
            _record_last_error(config, f"Failed to decrypt package {metadata['package_id']}: {exc}")
            return SyncActionResult(
                status="error",
                message=f"Failed to decrypt package {metadata['package_id']}. Check the sync passphrase.",
            )

        _write_receipt(sync_root, settings.device_id, metadata, result["status"], result["message"])
        if result["status"] == "imported":
            imported += 1
        elif result["status"] == "conflict":
            conflicts += 1
        else:
            skipped += 1

    if imported == 0 and conflicts == 0 and skipped == 0:
        return SyncActionResult(status="noop", message="No remote sync packages are waiting.")
    append_sync_history(
        config,
        action="import_remote",
        status="completed",
        message=f"Imported {imported} packages, {conflicts} conflicts, {skipped} skipped.",
        details={"imported": imported, "conflicts": conflicts, "skipped": skipped},
    )
    return SyncActionResult(
        status="completed",
        message=f"Imported {imported} packages, {conflicts} conflicts, {skipped} skipped.",
        payload={"imported": imported, "conflicts": conflicts, "skipped": skipped},
    )


def run_sync_now(config: AppConfig) -> SyncActionResult:
    settings = ensure_device_identity(config)
    validation_error = _validate_sync_configuration(config, settings, require_passphrase=True)
    if validation_error is not None:
        return validation_error

    export_events = export_new_event_package(config)
    export_persona = export_persona_sync_package(config)
    import_remote = import_remote_packages(config)

    last_error = ""
    statuses = [export_events.status, export_persona.status, import_remote.status]
    if "error" in statuses:
        last_error = " | ".join(
            result.message
            for result in (export_events, export_persona, import_remote)
            if result.status == "error"
        )
        _record_last_error(config, last_error)
        return SyncActionResult(status="error", message=last_error)

    state = _load_sync_state(config)
    state["last_sync_at"] = utc_now().isoformat()
    state["last_error"] = ""
    _save_sync_state(config, state)
    append_sync_history(
        config,
        action="sync_now",
        status="completed",
        message="Safe sync cycle completed.",
        details={
            "event_export": export_events.status,
            "persona_export": export_persona.status,
            "remote_import": import_remote.status,
        },
    )
    return SyncActionResult(
        status="completed",
        message="Safe sync cycle completed.",
        payload={
            "event_export": export_events.payload,
            "persona_export": export_persona.payload,
            "remote_import": import_remote.payload,
        },
    )


def get_sync_status(config: AppConfig) -> SyncStatusSummary:
    settings = ensure_device_identity(config)
    sync_root = _sync_root_path(settings)
    state = _load_sync_state(config)
    warnings = _build_status_warnings(config, settings, sync_root)
    pending_outgoing = _pending_outgoing_count(config, settings)
    pending_incoming = _pending_incoming_count(sync_root, settings) if sync_root else 0
    conflict_count = _conflict_count(sync_root) if sync_root else 0
    last_error = state.get("last_error", "")
    if warnings or last_error:
        health = "issue"
    elif not settings.sync_enabled:
        health = "paused"
    else:
        health = "healthy"
    return SyncStatusSummary(
        enabled=settings.sync_enabled,
        provider=settings.sync_provider,
        device_id=settings.device_id,
        device_name=settings.device_name,
        device_role=settings.device_role,
        sync_root_path=settings.sync_root_path,
        sync_passphrase_set=settings.sync_passphrase_set,
        sync_auto_start=settings.sync_auto_start,
        sync_interval_seconds=settings.sync_interval_seconds,
        last_sync_time=state.get("last_sync_at", ""),
        pending_outgoing_count=pending_outgoing,
        pending_incoming_count=pending_incoming,
        last_error=last_error,
        conflict_count=conflict_count,
        recent_history=load_sync_history(config, limit=8),
        health=health,
        warnings=warnings,
    )


def load_sync_history(config: AppConfig, *, limit: int = 10) -> list[dict[str, Any]]:
    if not config.sync_history_path.exists():
        return []
    lines = [
        line.strip()
        for line in config.sync_history_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records = [json.loads(line) for line in lines[-limit:]]
    records.reverse()
    return records


def append_sync_history(
    config: AppConfig,
    *,
    action: str,
    status: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    entry = {
        "timestamp": utc_now().isoformat(),
        "action": action,
        "status": status,
        "message": message,
        "details": details or {},
    }
    config.sync_history_path.parent.mkdir(parents=True, exist_ok=True)
    with config.sync_history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def start_sync_worker(config: AppConfig) -> SyncWorkerHandle | None:
    settings = load_project_settings(config)
    if not settings.sync_enabled or not settings.sync_auto_start:
        return None

    stop_event = threading.Event()
    thread = threading.Thread(
        target=_sync_worker_loop,
        args=(config, stop_event),
        daemon=True,
        name="pop-sync-worker",
    )
    thread.start()
    return SyncWorkerHandle(thread=thread, stop_event=stop_event)


def stop_sync_worker(handle: SyncWorkerHandle | None) -> None:
    if handle is None:
        return
    handle.stop_event.set()
    handle.thread.join(timeout=5)


def _sync_worker_loop(config: AppConfig, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        settings = load_project_settings(config)
        interval = max(15, settings.sync_interval_seconds)
        if settings.sync_enabled and settings.sync_auto_start:
            result = run_sync_now(config)
            _append_sync_log(
                config,
                {
                    "timestamp": utc_now().isoformat(),
                    "status": result.status,
                    "message": result.message,
                },
            )
        stop_event.wait(interval)


def _collect_pending_events(config: AppConfig, *, since: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with get_connection(config.database_path) as connection:
        rows = connection.execute(
            """
            SELECT session_id, feedback_status, feedback_note, feedback_updated_at
            FROM sessions
            WHERE feedback_updated_at IS NOT NULL
              AND (? = '' OR feedback_updated_at > ?)
            ORDER BY feedback_updated_at ASC, session_id ASC
            """,
            (since, since),
        ).fetchall()
        for row in rows:
            events.append(
                {
                    "event_type": "session_feedback",
                    "event_key": f"session_feedback:{row['session_id']}:{row['feedback_updated_at']}",
                    "session_id": row["session_id"],
                    "feedback_status": row["feedback_status"],
                    "feedback_note": row["feedback_note"],
                    "updated_at": row["feedback_updated_at"],
                }
            )

        intent_rows = connection.execute(
            """
            SELECT intent_id, review_status, review_note, review_updated_at
            FROM execution_intents
            WHERE review_updated_at IS NOT NULL
              AND (? = '' OR review_updated_at > ?)
            ORDER BY review_updated_at ASC, intent_id ASC
            """,
            (since, since),
        ).fetchall()
        for row in intent_rows:
            events.append(
                {
                    "event_type": "execution_review",
                    "event_key": f"execution_review:{row['intent_id']}:{row['review_updated_at']}",
                    "intent_id": row["intent_id"],
                    "review_status": row["review_status"],
                    "review_note": row["review_note"],
                    "updated_at": row["review_updated_at"],
                }
            )
    events.sort(key=lambda item: (item["updated_at"], item["event_key"]))
    return events


def _import_event_package(
    config: AppConfig,
    sync_root: Path,
    settings: ProjectSettings,
    metadata: dict[str, Any],
) -> dict[str, str]:
    encrypted_path = sync_root / metadata["encrypted_file"]
    payload_bytes = _decrypt_payload(config, metadata, encrypted_path.read_bytes())
    raw_lines = [line for line in payload_bytes.decode("utf-8").splitlines() if line.strip()]
    events = [json.loads(line) for line in raw_lines]
    conflicts: list[dict[str, Any]] = []
    applied = 0
    with get_connection(config.database_path) as connection:
        for event in events:
            if event["event_type"] == "session_feedback":
                session = get_session_record(connection, event["session_id"])
                if session is None:
                    conflicts.append(
                        {
                            "reason": "missing_session",
                            "event": event,
                            "package_id": metadata["package_id"],
                        }
                    )
                    continue
                if (
                    session.feedback_updated_at is not None
                    and session.feedback_updated_at.isoformat() >= event["updated_at"]
                ):
                    continue
                session.feedback_status = event["feedback_status"]
                session.feedback_note = event["feedback_note"]
                session.feedback_updated_at = datetime.fromisoformat(event["updated_at"])
                update_session_feedback(
                    connection,
                    session.session_id,
                    feedback_status=session.feedback_status,
                    feedback_note=session.feedback_note,
                    feedback_updated_at=session.feedback_updated_at.isoformat(),
                )
                if session.artifact_path:
                    write_json(Path(session.artifact_path), session.model_dump(mode="json"))
                if session.markdown_path:
                    Path(session.markdown_path).write_text(
                        render_session_markdown(session),
                        encoding="utf-8",
                    )
                applied += 1
                continue

            intent = get_execution_intent(connection, event["intent_id"])
            if intent is None:
                conflicts.append(
                    {
                        "reason": "missing_execution_intent",
                        "event": event,
                        "package_id": metadata["package_id"],
                    }
                )
                continue
            if (
                intent.review_updated_at is not None
                and intent.review_updated_at.isoformat() >= event["updated_at"]
            ):
                continue
            intent.review_status = event["review_status"]
            intent.review_note = event["review_note"]
            intent.review_updated_at = datetime.fromisoformat(event["updated_at"])
            artifact_path = write_execution_intent_artifact(config, intent)
            update_execution_intent(connection, intent, artifact_path=artifact_path)
            applied += 1

    if conflicts:
        _write_conflict(sync_root, metadata, conflicts)
        return {"status": "conflict", "message": f"Package {metadata['package_id']} created conflicts."}
    return {"status": "imported", "message": f"Imported {applied} event updates."}


def _import_persona_package(
    config: AppConfig,
    sync_root: Path,
    settings: ProjectSettings,
    metadata: dict[str, Any],
) -> dict[str, str]:
    if metadata.get("source_device_role") != "primary":
        _write_conflict(
            sync_root,
            metadata,
            [{"reason": "non_primary_persona_package", "metadata": metadata}],
        )
        return {"status": "conflict", "message": "Only primary persona packages are accepted."}

    if settings.device_role == "primary" and metadata.get("source_device_id") != settings.device_id:
        _write_conflict(
            sync_root,
            metadata,
            [{"reason": "remote_persona_conflicts_with_local_primary", "metadata": metadata}],
        )
        return {"status": "conflict", "message": "Primary devices keep local persona authoritative."}

    encrypted_path = sync_root / metadata["encrypted_file"]
    payload_bytes = _decrypt_payload(config, metadata, encrypted_path.read_bytes())
    payload = json.loads(payload_bytes.decode("utf-8"))
    persona_core = PersonaCore.model_validate(payload["persona_core"])
    daily_snapshots = [
        DailyPersonaSnapshot.model_validate(snapshot)
        for snapshot in payload.get("daily_snapshots", [])
    ]
    json_path, markdown_path = write_persona_core_files(config, persona_core)
    with get_connection(config.database_path) as connection:
        insert_persona_core_version(
            connection,
            version_id=new_id("pcv"),
            persona_core=persona_core,
            markdown_path=markdown_path,
        )
        for snapshot in daily_snapshots:
            existing = find_daily_persona_snapshot(
                connection,
                snapshot.date_range.date_from,
                snapshot.date_range.date_to,
                persona_core.snapshot_scope,
            )
            if existing is not None and json.loads(existing["payload_json"]) == snapshot.model_dump(mode="json"):
                continue
            if existing is not None:
                delete_daily_persona_snapshots(
                    connection,
                    snapshot.date_range.date_from,
                    snapshot.date_range.date_to,
                    persona_core.snapshot_scope,
                )
            _json_path, snapshot_markdown_path = write_daily_snapshot_files(config, snapshot)
            insert_daily_persona_snapshot(
                connection,
                snapshot,
                snapshot_markdown_path,
                persona_core.snapshot_scope,
            )

    append_sync_history(
        config,
        action="import_persona",
        status="imported",
        message="Imported remote primary persona package.",
        details={"package_id": metadata["package_id"], "persona_json_path": str(json_path)},
    )
    return {"status": "imported", "message": "Imported remote primary persona package."}


def _validate_sync_configuration(
    config: AppConfig,
    settings: ProjectSettings,
    *,
    require_passphrase: bool,
) -> SyncActionResult | None:
    if settings.sync_provider != SYNC_PROVIDER:
        return SyncActionResult(status="error", message="Only google_drive_folder sync is supported.")
    if not settings.sync_root_path.strip():
        return SyncActionResult(status="error", message="Sync root path is not configured.")
    sync_root = _sync_root_path(settings)
    if sync_root is None:
        return SyncActionResult(status="error", message="Sync root path is not configured.")
    try:
        _ensure_sync_root_structure(sync_root)
    except OSError:
        return SyncActionResult(
            status="error",
            message="Sync root is not accessible. Check whether Google Drive is mounted.",
        )
    if settings.device_role not in {"primary", "secondary"}:
        return SyncActionResult(
            status="error",
            message="Device role is misconfigured. Choose primary or secondary again.",
        )
    if require_passphrase and load_sync_key(config) is None:
        return SyncActionResult(status="error", message="Sync passphrase is not set on this device.")
    return None


def load_sync_key(config: AppConfig) -> bytes | None:
    if not config.sync_secret_path.exists():
        return None
    payload = json.loads(config.sync_secret_path.read_text(encoding="utf-8"))
    key_b64 = str(payload.get("key_b64", "")).strip()
    if key_b64:
        return key_b64.encode("ascii")
    legacy_passphrase = str(payload.get("passphrase", "")).strip()
    if not legacy_passphrase:
        return None
    key = _derive_local_sync_key(legacy_passphrase)
    write_json(
        config.sync_secret_path,
        {
            "key_b64": key.decode("ascii"),
            "saved_at": payload.get("saved_at") or utc_now().isoformat(),
            "version": 2,
        },
    )
    return key


def _encrypt_payload(config: AppConfig, payload: bytes) -> dict[str, Any]:
    key = load_sync_key(config)
    if key is None:
        raise ValueError("Sync passphrase is not set.")
    token = Fernet(key).encrypt(payload)
    return {
        "ciphertext": token,
        "metadata": {
            "algorithm": "fernet-aes128-cbc-hmac",
            "kdf": "scrypt-fixed-salt-v1",
        },
    }


def _decrypt_payload(config: AppConfig, metadata: dict[str, Any], payload: bytes) -> bytes:
    key = load_sync_key(config)
    if key is None:
        raise InvalidToken("missing passphrase")
    return Fernet(key).decrypt(payload)


def _derive_local_sync_key(passphrase: str) -> bytes:
    key = hashlib.scrypt(
        passphrase.encode("utf-8"),
        salt=SYNC_KDF_SALT,
        n=16384,
        r=8,
        p=1,
        dklen=32,
    )
    return base64.urlsafe_b64encode(key)


def _recent_snapshots(
    snapshots: list[DailyPersonaSnapshot],
    *,
    days: int,
) -> list[DailyPersonaSnapshot]:
    if not snapshots:
        return []
    cutoff = utc_now().date() - timedelta(days=max(days, 1) - 1)
    selected: list[DailyPersonaSnapshot] = []
    for snapshot in snapshots:
        try:
            snapshot_day = date.fromisoformat(snapshot.date_range.date_to)
        except ValueError:
            continue
        if snapshot_day >= cutoff:
            selected.append(snapshot)
    return selected or snapshots[-days:]


def _build_status_warnings(
    config: AppConfig,
    settings: ProjectSettings,
    sync_root: Path | None,
) -> list[str]:
    warnings: list[str] = []
    if sync_root is None:
        warnings.append("Sync root is missing. Choose a Google Drive folder first.")
    else:
        try:
            _ensure_sync_root_structure(sync_root)
        except OSError:
            warnings.append(
                "Sync root is not accessible right now. Check whether Google Drive is mounted."
            )
    if settings.device_role not in {"primary", "secondary"}:
        warnings.append("Device role is misconfigured. Choose primary or secondary again.")
    if not settings.sync_passphrase_set or load_sync_key(config) is None:
        warnings.append("Sync passphrase is missing on this device.")
    return warnings


def _sync_root_path(settings: ProjectSettings) -> Path | None:
    raw = settings.sync_root_path.strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def _require_sync_root(settings: ProjectSettings) -> Path:
    sync_root = _sync_root_path(settings)
    if sync_root is None:
        raise ValueError("Sync root is not configured.")
    return sync_root


def _ensure_sync_root_structure(sync_root: Path) -> None:
    for path in (
        sync_root / "manifests" / "devices",
        sync_root / "events",
        sync_root / "packages" / "persona" / "latest",
        sync_root / "packages" / "persona" / "history",
        sync_root / "receipts",
        sync_root / "conflicts",
        sync_root / "versions",
    ):
        path.mkdir(parents=True, exist_ok=True)


def _write_device_manifest(sync_root: Path, settings: ProjectSettings) -> None:
    manifest_path = sync_root / "manifests" / "devices" / f"{settings.device_id}.json"
    write_json(
        manifest_path,
        {
            "device_id": settings.device_id,
            "device_name": settings.device_name,
            "device_role": settings.device_role,
            "provider": settings.sync_provider,
            "updated_at": utc_now().isoformat(),
        },
    )


def _relative_to_root(sync_root: Path, path: Path) -> str:
    return str(path.relative_to(sync_root))


def _load_sync_state(config: AppConfig) -> dict[str, Any]:
    if not config.sync_state_path.exists():
        return {
            "last_event_sequence": 0,
            "last_event_export_at": "",
            "last_persona_exported_at": "",
            "last_sync_at": "",
            "last_error": "",
        }
    return json.loads(config.sync_state_path.read_text(encoding="utf-8"))


def _save_sync_state(config: AppConfig, payload: dict[str, Any]) -> None:
    write_json(config.sync_state_path, payload)


def _record_last_error(config: AppConfig, message: str) -> None:
    state = _load_sync_state(config)
    state["last_error"] = message
    _save_sync_state(config, state)
    append_sync_history(config, action="error", status="error", message=message)


def _pending_outgoing_count(config: AppConfig, settings: ProjectSettings) -> int:
    state = _load_sync_state(config)
    pending_events = len(_collect_pending_events(config, since=state.get("last_event_export_at", "")))
    pending_persona = 0
    if settings.device_role == "primary":
        with get_connection(config.database_path) as connection:
            persona_core = get_current_persona_core(connection, snapshot_scope="all")
        if persona_core is not None and persona_core.last_updated is not None:
            if persona_core.last_updated.isoformat() > state.get("last_persona_exported_at", ""):
                pending_persona = 1
    return pending_events + pending_persona


def _iter_pending_remote_package_metadata(
    sync_root: Path,
    settings: ProjectSettings,
) -> list[tuple[Path, dict[str, Any]]]:
    metadata_items: list[tuple[Path, dict[str, Any]]] = []
    for pattern in ("events/*/*.meta.json", "packages/persona/history/*.meta.json"):
        for path in sorted(sync_root.glob(pattern)):
            metadata = json.loads(path.read_text(encoding="utf-8"))
            if metadata.get("source_device_id") == settings.device_id:
                continue
            receipt_path = _receipt_path(sync_root, settings.device_id, metadata["package_id"])
            if receipt_path.exists():
                continue
            metadata_items.append((path, metadata))
    metadata_items.sort(key=lambda item: (item[1].get("created_at", ""), item[1].get("package_id", "")))
    return metadata_items


def _pending_incoming_count(sync_root: Path, settings: ProjectSettings) -> int:
    return len(_iter_pending_remote_package_metadata(sync_root, settings))


def _receipt_path(sync_root: Path, device_id: str, package_id: str) -> Path:
    return sync_root / "receipts" / device_id / f"{package_id}.json"


def _write_receipt(
    sync_root: Path,
    device_id: str,
    metadata: dict[str, Any],
    status: str,
    message: str,
) -> None:
    receipt_path = _receipt_path(sync_root, device_id, metadata["package_id"])
    write_json(
        receipt_path,
        {
            "package_id": metadata["package_id"],
            "package_type": metadata["package_type"],
            "source_device_id": metadata.get("source_device_id", ""),
            "status": status,
            "message": message,
            "processed_at": utc_now().isoformat(),
        },
    )


def _write_conflict(sync_root: Path, metadata: dict[str, Any], payload: list[dict[str, Any]]) -> None:
    conflict_path = sync_root / "conflicts" / f"{metadata['package_id']}.json"
    write_json(
        conflict_path,
        {
            "package_id": metadata["package_id"],
            "package_type": metadata["package_type"],
            "created_at": metadata.get("created_at", ""),
            "source_device_id": metadata.get("source_device_id", ""),
            "source_device_role": metadata.get("source_device_role", ""),
            "details": payload,
        },
    )


def _conflict_count(sync_root: Path) -> int:
    return sum(1 for _path in sync_root.glob("conflicts/*.json"))


def _append_sync_log(config: AppConfig, payload: dict[str, Any]) -> None:
    log_path = config.logs_dir / "sync.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
