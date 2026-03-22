from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pop_cockpit.config import AppConfig
from pop_cockpit.extractor import DailyExtractionResult, extract_daily_snapshot
from pop_cockpit.importer import ImportFileResult, ImportSummary, import_folder_to_workspace
from pop_cockpit.persona import PersonaResult, rebuild_persona_core
from pop_cockpit.schemas import WorkflowRunRecord
from pop_cockpit.settings import load_project_settings
from pop_cockpit.utils import new_id, utc_now, write_json


@dataclass(slots=True)
class WorkflowResult:
    status: str
    message: str
    import_summary: ImportSummary | None = None
    extraction_result: DailyExtractionResult | None = None
    persona_result: PersonaResult | None = None
    archived_count: int = 0
    failed_moved_count: int = 0
    run_record: WorkflowRunRecord | None = None
    artifact_path: Path | None = None
    log_path: Path | None = None


def run_daily_workflow(config: AppConfig, *, command_name: str = "daily") -> WorkflowResult:
    settings = load_project_settings(config)
    inbox_path_value = settings.inbox_path or (
        settings.scheduler.inbox_path if settings.scheduler is not None else ""
    )
    if not inbox_path_value:
        return WorkflowResult(
            status="missing_config",
            message="No inbox path configured. Run `pop scheduler install --inbox <path>` first.",
        )

    inbox_path = Path(inbox_path_value).expanduser()
    inbox_path.mkdir(parents=True, exist_ok=True)
    workflow_date = date.today().isoformat()

    import_summary = import_folder_to_workspace(config, inbox_path)
    archived_count, failed_moved_count = apply_inbox_archive_behavior(
        import_summary,
        inbox_path=inbox_path,
        archive_path=Path(settings.archive_path).expanduser() if settings.archive_path else None,
        failed_path=Path(settings.failed_path).expanduser() if settings.failed_path else None,
        archive_after_import=settings.archive_after_import,
        workflow_date=workflow_date,
    )
    extraction_result = extract_daily_snapshot(
        config,
        workflow_date,
        workflow_date,
        overwrite=True,
    )
    persona_result = rebuild_persona_core(config)

    run_id = new_id("wf")
    artifact_path = config.logs_dir / f"workflow_run_{run_id}.json"
    log_path = config.logs_dir / "workflow.log"
    run_record = WorkflowRunRecord(
        run_id=run_id,
        command_name=command_name,
        created_at=utc_now(),
        workflow_date=workflow_date,
        inbox_path=str(inbox_path),
        imported_count=import_summary.imported_count,
        skipped_count=import_summary.skipped_count,
        duplicate_count=import_summary.duplicate_count,
        unsupported_count=import_summary.unsupported_count,
        archived_count=archived_count,
        failed_moved_count=failed_moved_count,
        daily_snapshot_status=extraction_result.status,
        daily_snapshot_id=extraction_result.snapshot.id if extraction_result.snapshot else None,
        persona_rebuild_status=persona_result.status,
        persona_core_scope=persona_result.persona_core.snapshot_scope
        if persona_result.persona_core is not None
        else "all",
        artifact_path=str(artifact_path),
        log_path=str(log_path),
    )
    write_json(artifact_path, run_record.model_dump(mode="json"))
    _append_workflow_log(log_path, run_record)
    return WorkflowResult(
        status="completed",
        message=f"Workflow {command_name} completed for {workflow_date}.",
        import_summary=import_summary,
        extraction_result=extraction_result,
        persona_result=persona_result,
        archived_count=archived_count,
        failed_moved_count=failed_moved_count,
        run_record=run_record,
        artifact_path=artifact_path,
        log_path=log_path,
    )


def format_workflow_result(result: WorkflowResult) -> str:
    lines = [result.message]
    if result.import_summary is None or result.extraction_result is None or result.persona_result is None:
        return "\n".join(lines)

    lines.extend(
        [
            f"imported: {result.import_summary.imported_count}",
            f"skipped: {result.import_summary.skipped_count}",
            f"duplicates: {result.import_summary.duplicate_count}",
            f"unsupported: {result.import_summary.unsupported_count}",
            f"archived: {result.archived_count}",
            f"failed_moved: {result.failed_moved_count}",
            f"daily_snapshot_status: {result.extraction_result.status}",
            f"persona_rebuild_status: {result.persona_result.status}",
        ]
    )
    if result.extraction_result.snapshot is not None:
        lines.append(f"daily_snapshot_id: {result.extraction_result.snapshot.id}")
    if result.artifact_path is not None:
        lines.append(f"log_artifact: {result.artifact_path}")
    if result.log_path is not None:
        lines.append(f"rolling_log: {result.log_path}")
    return "\n".join(lines)


def _append_workflow_log(log_path: Path, run_record: WorkflowRunRecord) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "run_id": run_record.run_id,
        "created_at": run_record.created_at.isoformat(),
        "workflow_date": run_record.workflow_date,
        "imported": run_record.imported_count,
        "skipped": run_record.skipped_count,
        "duplicates": run_record.duplicate_count,
        "unsupported": run_record.unsupported_count,
        "archived": run_record.archived_count,
        "failed_moved": run_record.failed_moved_count,
        "daily_snapshot_status": run_record.daily_snapshot_status,
        "persona_rebuild_status": run_record.persona_rebuild_status,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, ensure_ascii=False) + "\n")


def apply_inbox_archive_behavior(
    summary: ImportSummary,
    *,
    inbox_path: Path,
    archive_path: Path | None,
    failed_path: Path | None,
    archive_after_import: bool,
    workflow_date: str,
) -> tuple[int, int]:
    if not archive_after_import or archive_path is None:
        return (0, 0)

    archived_count = 0
    failed_moved_count = 0
    archive_root = archive_path.expanduser().resolve() / workflow_date
    failed_root = failed_path.expanduser().resolve() / workflow_date if failed_path is not None else None
    for result in summary.results:
        if not result.path.exists():
            continue
        try:
            relative_path = result.path.resolve().relative_to(inbox_path.resolve())
        except ValueError:
            relative_path = Path(result.path.name)

        if result.status in {"imported", "duplicate"}:
            destination = _unique_destination(archive_root / relative_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(result.path), str(destination))
            archived_count += 1
        elif failed_root is not None and result.status not in {"imported", "duplicate"}:
            destination = _unique_destination(failed_root / relative_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(result.path), str(destination))
            failed_moved_count += 1
    return archived_count, failed_moved_count


def _unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Unable to allocate archive destination for {path}")
