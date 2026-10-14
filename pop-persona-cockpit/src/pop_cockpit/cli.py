from __future__ import annotations

import zipfile
from pathlib import Path

import typer

from pop_cockpit.autostart import (
    autostart_status,
    disable_autostart,
    enable_autostart,
    format_autostart_status,
)
from pop_cockpit.audit import (
    audit_record_to_json,
    audit_records_to_json,
    format_audit_detail,
    format_audit_list,
    list_audit_entries,
    load_audit_entry,
)
from pop_cockpit.browser_capture import capture_status
from pop_cockpit.chatgpt_importer import format_chatgpt_import_summary, import_chatgpt_export
from pop_cockpit.config import AppConfig
from pop_cockpit.llm_api import provider_status_text
from pop_cockpit.execution import (
    format_execution_detail,
    format_execution_list,
    get_execution_detail,
    list_execution_items,
    reject_execution_intent,
    simulate_execution_intent,
)
from pop_cockpit.extractor import (
    backfill_daily_snapshots,
    extract_daily_snapshot,
    format_backfill_result,
    format_daily_extraction_result,
)
from pop_cockpit.importer import (
    format_import_summary,
    import_file_to_workspace,
    import_folder_to_workspace,
)
from pop_cockpit.injector import ask_question, format_ask_result
from pop_cockpit.lifecycle import POP_URL, open_local_browser, run_pop_service
from pop_cockpit.persona import (
    export_persona_core,
    export_persona_package,
    format_persona_core_summary,
    format_persona_result,
    rebuild_persona_core,
    show_persona_core,
)
from pop_cockpit.scheduler import (
    disable_scheduler,
    enable_scheduler,
    format_scheduler_result,
    install_scheduler,
    scheduler_status,
)
from pop_cockpit.settings import load_project_settings
from pop_cockpit.storage import (
    ensure_runtime,
    get_connection,
    get_current_persona_core_version,
    list_session_records,
)
from pop_cockpit.sync import (
    export_persona_sync_package,
    get_sync_status,
    import_remote_packages,
    initialize_sync,
    pause_sync,
    resume_sync,
    run_sync_now,
    set_sync_passphrase,
)
from pop_cockpit.workflow import format_workflow_result, run_daily_workflow

app = typer.Typer(
    help="POP Persona Cockpit: local-first CLI for persona imports, extraction, and prompt assembly."
)
import_app = typer.Typer(help="Import chat logs and notes into the local workspace.")
extract_app = typer.Typer(help="Extract structured daily persona signals.")
persona_app = typer.Typer(help="Work with the stable persona core.")
audit_app = typer.Typer(help="Inspect persona-assisted audit logs.")
workflow_app = typer.Typer(help="Run daily or weekly cockpit workflows.")
scheduler_app = typer.Typer(help="Install and manage the local macOS LaunchAgent scheduler.")
execution_app = typer.Typer(help="Inspect and simulate persona-guided execution intents.")
autostart_app = typer.Typer(help="Enable or disable POP at login on macOS.")
sync_app = typer.Typer(help="Manage POP Sync Helper Mini for safe multi-device syncing.")

app.add_typer(import_app, name="import")
app.add_typer(extract_app, name="extract")
app.add_typer(persona_app, name="persona")
app.add_typer(audit_app, name="audit")
app.add_typer(workflow_app, name="workflow")
app.add_typer(scheduler_app, name="scheduler")
app.add_typer(execution_app, name="execution")
app.add_typer(autostart_app, name="autostart")
app.add_typer(sync_app, name="sync")


def _config() -> AppConfig:
    config = AppConfig.load()
    ensure_runtime(config)
    return config


@app.callback()
def main() -> None:
    """Bootstrap local storage before any subcommand runs."""
    _config()


@app.command()
def status() -> None:
    """Show a compact daily-use status summary."""
    config = _config()
    settings = load_project_settings(config)
    scheduler = scheduler_status(config)
    autostart = autostart_status(config)
    capture = capture_status(config)
    with get_connection(config.database_path) as connection:
        persona_core = get_current_persona_core_version(connection, snapshot_scope="all")
        sessions = list_session_records(connection, limit=10)
    typer.echo("POP is ready.")
    typer.echo(f"web_ui: {POP_URL}")
    typer.echo(f"autostart: {'on' if autostart.enabled else 'off'}")
    typer.echo(f"automatic_updates: {'on' if scheduler.enabled else 'off'}")
    typer.echo(f"auto_capture: {'on' if capture.capture_endpoint_available else 'off'}")
    typer.echo(f"browser_auto_open: {'on' if settings.auto_open_browser else 'off'}")
    typer.echo(f"inbox: {settings.inbox_path or 'not configured'}")
    typer.echo(f"archive: {settings.archive_path or 'not configured'}")
    typer.echo(f"archive_after_import: {'yes' if settings.archive_after_import else 'no'}")
    typer.echo(f"provider_mode: {settings.provider_mode}")
    typer.echo(f"default_model: {settings.default_model or 'not configured'}")
    typer.echo(f"provider_last_test: {provider_status_text(settings)}")
    typer.echo(f"persona_ready: {'yes' if persona_core is not None else 'no'}")
    typer.echo(f"saved_analyses: {len(sessions)}")
    sync_status = get_sync_status(config)
    typer.echo(f"sync: {'on' if sync_status.enabled else 'off'}")
    typer.echo(f"sync_role: {sync_status.device_role}")
    typer.echo(f"sync_root: {sync_status.sync_root_path or 'not configured'}")
    typer.echo(f"sync_last: {sync_status.last_sync_time or 'never'}")
    typer.echo(f"data_dir: {config.data_dir}")


def _start_web_shell(*, auto_open_browser_override: bool | None = None) -> None:
    config = _config()
    settings = load_project_settings(config)
    autostart = autostart_status(config)
    browser_auto_open = (
        settings.auto_open_browser
        if auto_open_browser_override is None
        else auto_open_browser_override
    )
    typer.echo(f"POP is running at {POP_URL}")
    typer.echo(f"Autostart: {'enabled' if autostart.enabled else 'disabled'}")
    typer.echo(f"Browser auto-open: {'on' if browser_auto_open else 'off'}")
    typer.echo("Press Ctrl+C to stop the local server.")
    run_pop_service(config, auto_open_browser=browser_auto_open)


@app.command("web")
def web_command() -> None:
    """Start the local web UI shell."""
    _start_web_shell(auto_open_browser_override=False)


@app.command("start")
def start_command() -> None:
    """Start the local web UI with a simpler daily-use entrypoint."""
    _start_web_shell()


@app.command("open")
def open_command() -> None:
    """Open the local POP UI in the default browser."""
    if not open_local_browser(POP_URL):
        typer.secho(f"error: could not open {POP_URL}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Opened {POP_URL}")


@import_app.command("file")
def import_file_command(path: Path) -> None:
    """Import one supported file into the local workspace."""
    config = _config()
    try:
        summary = import_file_to_workspace(config, path)
    except (FileNotFoundError, IsADirectoryError) as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(format_import_summary(summary))


@import_app.command("folder")
def import_folder_command(path: Path) -> None:
    """Import all supported files from a folder recursively."""
    config = _config()
    try:
        summary = import_folder_to_workspace(config, path)
    except (FileNotFoundError, NotADirectoryError) as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(format_import_summary(summary))


@import_app.command("chatgpt-export")
def import_chatgpt_export_command(path: Path) -> None:
    """Import a ChatGPT export zip or folder."""
    config = _config()
    try:
        summary = import_chatgpt_export(config, path)
    except (FileNotFoundError, ValueError, zipfile.BadZipFile) as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(format_chatgpt_import_summary(summary))


@extract_app.command("daily")
def extract_daily(
    date_from: str = typer.Option(..., "--from", help="Start date in YYYY-MM-DD format."),
    date_to: str = typer.Option(..., "--to", help="End date in YYYY-MM-DD format."),
) -> None:
    """Extract one daily persona snapshot for the selected date range."""
    config = _config()
    try:
        result = extract_daily_snapshot(config, date_from, date_to)
    except ValueError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(format_daily_extraction_result(result))


@extract_app.command("backfill")
def extract_backfill(
    date_from: str = typer.Option(..., "--from", help="Start date in YYYY-MM-DD format."),
    date_to: str = typer.Option(..., "--to", help="End date in YYYY-MM-DD format."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Replace existing snapshots."),
    source_type: str | None = typer.Option(
        None,
        "--source-type",
        help="Only backfill records from one source type, for example chatgpt_export.",
    ),
) -> None:
    """Backfill daily persona snapshots across a historical date range."""
    config = _config()
    try:
        result = backfill_daily_snapshots(
            config,
            date_from,
            date_to,
            overwrite=overwrite,
            source_type=source_type,
        )
    except ValueError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(format_backfill_result(result))


@persona_app.command("rebuild")
def persona_rebuild(
    scope: str = typer.Option("all", "--scope", help="Snapshot scope to aggregate."),
) -> None:
    """Rebuild the stable persona core from daily snapshots."""
    config = _config()
    result = rebuild_persona_core(config, snapshot_scope=scope)
    typer.echo(format_persona_result(result))


@persona_app.command("show")
def persona_show(
    scope: str = typer.Option("all", "--scope", help="Snapshot scope to show."),
) -> None:
    """Show the current persona core."""
    config = _config()
    result = show_persona_core(config, snapshot_scope=scope)
    if result.persona_core is None:
        typer.echo(result.message)
        return
    typer.echo(format_persona_core_summary(result.persona_core))


@persona_app.command("export")
def persona_export(
    scope: str = typer.Option("all", "--scope", help="Snapshot scope to export."),
) -> None:
    """Export the current persona core to JSON and Markdown."""
    config = _config()
    result = export_persona_core(config, snapshot_scope=scope)
    typer.echo(format_persona_result(result))


@persona_app.command("export-package")
def persona_export_package_command(
    scope: str = typer.Option("all", "--scope", help="Snapshot scope to package."),
) -> None:
    """Export a portable persona package for local backup or transfer."""
    config = _config()
    result = export_persona_package(config, snapshot_scope=scope)
    typer.echo(result.message)
    if result.package_path is not None:
        typer.echo(f"package: {result.package_path}")


@app.command()
def ask(
    question: str,
    scope: str = typer.Option("all", "--scope", help="Persona scope to use."),
    days: int = typer.Option(7, "--days", help="Number of recent snapshot days to include."),
    source_type: str | None = typer.Option(
        None,
        "--source-type",
        help="Limit retrieved memories to one source type.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print and save the assembled prompt package without calling a provider.",
    ),
) -> None:
    """Assemble a persona-assisted prompt package for a new question."""
    config = _config()
    try:
        result = ask_question(
            config,
            question,
            snapshot_scope=scope,
            days=days,
            source_type=source_type,
            dry_run=dry_run,
        )
    except ValueError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(format_ask_result(result))
    if result.prompt_package:
        typer.echo("")
        typer.echo(result.prompt_package.rstrip())


@audit_app.command("list")
def audit_list(
    scope: str | None = typer.Option(None, "--scope", help="Filter by snapshot scope."),
    limit: int = typer.Option(20, "--limit", help="Maximum number of records to show."),
    mode: str | None = typer.Option(None, "--mode", help="Filter by mode, for example dry_run."),
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """List recent audit records."""
    config = _config()
    if limit <= 0:
        typer.secho("error: --limit must be a positive integer.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    records = list_audit_entries(config, snapshot_scope=scope, mode=mode, limit=limit)
    if as_json:
        typer.echo(audit_records_to_json(records))
        return
    typer.echo(format_audit_list(records))


@audit_app.command("show")
def audit_show(
    session_id: str,
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Show one audit record by session id."""
    config = _config()
    result = load_audit_entry(config, session_id)
    if result.audit_record is None:
        typer.echo(result.message)
        raise typer.Exit(code=1)
    if as_json:
        typer.echo(audit_record_to_json(result.audit_record))
        return
    typer.echo(format_audit_detail(result.audit_record))


@workflow_app.command("daily")
def workflow_daily() -> None:
    """Run the configured daily import, extraction, and persona rebuild workflow."""
    config = _config()
    result = run_daily_workflow(config, command_name="daily")
    typer.echo(format_workflow_result(result))


@workflow_app.command("run-now")
def workflow_run_now() -> None:
    """Run the same workflow immediately."""
    config = _config()
    result = run_daily_workflow(config, command_name="run-now")
    typer.echo(format_workflow_result(result))


@workflow_app.command("weekly")
def workflow_weekly() -> None:
    """Placeholder for the weekly workflow."""
    typer.echo("pending: Weekly workflow will be implemented after snapshot aggregation is ready.")


@scheduler_app.command("install")
def scheduler_install(
    hour: int = typer.Option(..., "--hour", help="Scheduled hour in local time."),
    minute: int = typer.Option(..., "--minute", help="Scheduled minute in local time."),
    inbox: Path = typer.Option(..., "--inbox", help="Inbox folder to scan during the daily workflow."),
) -> None:
    """Install or update the LaunchAgent plist without enabling it."""
    config = _config()
    try:
        result = install_scheduler(config, hour=hour, minute=minute, inbox_path=inbox)
    except ValueError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(format_scheduler_result(result))


@scheduler_app.command("enable")
def scheduler_enable() -> None:
    """Load the installed LaunchAgent into launchd."""
    config = _config()
    result = enable_scheduler(config)
    if result.status == "error":
        typer.secho(format_scheduler_result(result), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(format_scheduler_result(result))


@scheduler_app.command("disable")
def scheduler_disable() -> None:
    """Unload the LaunchAgent without deleting project data."""
    config = _config()
    result = disable_scheduler(config)
    if result.status == "error":
        typer.secho(format_scheduler_result(result), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(format_scheduler_result(result))


@scheduler_app.command("status")
def scheduler_status_command() -> None:
    """Show current scheduler configuration and launchd status."""
    config = _config()
    result = scheduler_status(config)
    typer.echo(format_scheduler_result(result))


@autostart_app.command("enable")
def autostart_enable_command() -> None:
    """Enable POP to start automatically when you log in."""
    config = _config()
    result = enable_autostart(config)
    if result.status == "error":
        typer.secho(format_autostart_status(result), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(format_autostart_status(result))


@autostart_app.command("disable")
def autostart_disable_command() -> None:
    """Disable automatic start on login."""
    config = _config()
    result = disable_autostart(config)
    if result.status == "error":
        typer.secho(format_autostart_status(result), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(format_autostart_status(result))


@autostart_app.command("status")
def autostart_status_command() -> None:
    """Show macOS autostart status."""
    config = _config()
    result = autostart_status(config)
    typer.echo(format_autostart_status(result))


@execution_app.command("list")
def execution_list(
    limit: int = typer.Option(20, "--limit", help="Maximum number of execution intents to show."),
) -> None:
    """List recent execution intents."""
    if limit <= 0:
        typer.secho("error: --limit must be a positive integer.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    config = _config()
    intents, _ = list_execution_items(config, limit=limit)
    typer.echo(format_execution_list(intents))


@execution_app.command("show")
def execution_show(intent_id: str) -> None:
    """Show one execution intent and its latest simulator results."""
    config = _config()
    detail = get_execution_detail(config, intent_id)
    if detail.intent is None:
        typer.echo("Execution intent not found.")
        raise typer.Exit(code=1)
    typer.echo(format_execution_detail(detail))


@execution_app.command("simulate")
def execution_simulate(intent_id: str) -> None:
    """Run the local simulator for one execution intent."""
    config = _config()
    result = simulate_execution_intent(config, intent_id)
    if result.intent is None:
        typer.secho(result.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(result.message)
    typer.echo("")
    typer.echo(format_execution_detail(get_execution_detail(config, intent_id)))


@execution_app.command("reject")
def execution_reject(intent_id: str) -> None:
    """Reject one execution intent without running anything."""
    config = _config()
    result = reject_execution_intent(config, intent_id)
    if result.intent is None:
        typer.secho(result.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(result.message)
    typer.echo("")
    typer.echo(format_execution_detail(get_execution_detail(config, intent_id)))


@sync_app.command("init")
def sync_init_command(
    provider: str = typer.Option(..., "--provider", help="Sync provider, currently google_drive_folder."),
    root: str = typer.Option(..., "--root", help="Chosen Google Drive sync folder path."),
    role: str = typer.Option(..., "--role", help="Device role: primary or secondary."),
    name: str = typer.Option(..., "--name", help="Human-readable device name."),
) -> None:
    """Initialize POP Sync Helper Mini for this device."""
    config = _config()
    result = initialize_sync(
        config,
        root_path=root,
        role=role,
        device_name=name,
        provider=provider,
    )
    if result.status == "error":
        typer.secho(result.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(result.message)
    if result.payload is not None:
        typer.echo(f"device_id: {result.payload['device_id']}")
        typer.echo(f"sync_root_path: {result.payload['sync_root_path']}")


@sync_app.command("status")
def sync_status_command() -> None:
    """Show POP sync status for this device."""
    config = _config()
    summary = get_sync_status(config)
    typer.echo(f"enabled: {'yes' if summary.enabled else 'no'}")
    typer.echo(f"provider: {summary.provider}")
    typer.echo(f"device_role: {summary.device_role}")
    typer.echo(f"device_id: {summary.device_id}")
    typer.echo(f"device_name: {summary.device_name}")
    typer.echo(f"sync_root_path: {summary.sync_root_path or 'not configured'}")
    typer.echo(f"last_sync_time: {summary.last_sync_time or 'never'}")
    typer.echo(f"pending_outgoing_count: {summary.pending_outgoing_count}")
    typer.echo(f"pending_incoming_count: {summary.pending_incoming_count}")
    typer.echo(f"conflict_count: {summary.conflict_count}")
    typer.echo(f"last_error: {summary.last_error or 'none'}")


@sync_app.command("now")
def sync_now_command() -> None:
    """Push local packages and pull remote packages now."""
    config = _config()
    result = run_sync_now(config)
    if result.status == "error":
        typer.secho(result.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(result.message)


@sync_app.command("pause")
def sync_pause_command() -> None:
    """Pause automatic sync on this device."""
    config = _config()
    typer.echo(pause_sync(config).message)


@sync_app.command("resume")
def sync_resume_command() -> None:
    """Resume automatic sync on this device."""
    config = _config()
    typer.echo(resume_sync(config).message)


@sync_app.command("export-persona")
def sync_export_persona_command() -> None:
    """Export the latest primary persona package into the sync folder."""
    config = _config()
    result = export_persona_sync_package(config, force=True)
    if result.status == "error":
        typer.secho(result.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(result.message)
    if result.payload is not None:
        typer.echo(f"package_id: {result.payload['package_id']}")
        typer.echo(f"metadata_path: {result.payload['metadata_path']}")


@sync_app.command("import-remote")
def sync_import_remote_command() -> None:
    """Import unseen remote sync packages into the local workspace."""
    config = _config()
    result = import_remote_packages(config)
    if result.status == "error":
        typer.secho(result.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(result.message)


@sync_app.command("set-passphrase")
def sync_set_passphrase_command(
    passphrase: str = typer.Option(
        "",
        "--passphrase",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Local sync passphrase used to encrypt sync packages.",
    ),
) -> None:
    """Set or update the local sync passphrase."""
    config = _config()
    result = set_sync_passphrase(config, passphrase)
    if result.status == "error":
        typer.secho(result.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.echo(result.message)


if __name__ == "__main__":
    app()
