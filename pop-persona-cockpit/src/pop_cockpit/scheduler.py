from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from pop_cockpit.config import AppConfig
from pop_cockpit.schemas import ProjectSettings, SchedulerConfig
from pop_cockpit.settings import load_project_settings, save_project_settings

SCHEDULER_LABEL = "com.zhangbin.pop-persona-cockpit.daily"


@dataclass(slots=True)
class SchedulerResult:
    status: str
    message: str
    plist_path: Path | None = None
    label: str = SCHEDULER_LABEL
    scheduled_time: str = ""
    inbox_path: str = ""
    installed: bool = False
    enabled: bool = False


def install_scheduler(config: AppConfig, *, hour: int, minute: int, inbox_path: Path) -> SchedulerResult:
    _validate_schedule(hour, minute)
    config.ensure_directories()

    resolved_inbox = inbox_path.expanduser().resolve()
    resolved_inbox.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agent_plist_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    command_path, command_args = resolve_workflow_command(config)
    stdout_log_path = config.logs_dir / "scheduler.stdout.log"
    stderr_log_path = config.logs_dir / "scheduler.stderr.log"
    plist_payload = build_launch_agent_plist(
        config=config,
        label=SCHEDULER_LABEL,
        hour=hour,
        minute=minute,
        command_args=command_args,
        stdout_log_path=stdout_log_path,
        stderr_log_path=stderr_log_path,
    )
    with plist_path.open("wb") as handle:
        plistlib.dump(plist_payload, handle, sort_keys=True)

    settings = load_project_settings(config)
    settings.inbox_path = str(resolved_inbox)
    settings.scheduler = SchedulerConfig(
        label=SCHEDULER_LABEL,
        hour=hour,
        minute=minute,
        inbox_path=str(resolved_inbox),
        plist_path=str(plist_path),
        command_path=command_path,
        command_args=command_args,
        stdout_log_path=str(stdout_log_path),
        stderr_log_path=str(stderr_log_path),
    )
    save_project_settings(config, settings)

    return SchedulerResult(
        status="installed",
        message="LaunchAgent plist installed. Run `pop scheduler enable` to load it.",
        plist_path=plist_path,
        scheduled_time=_format_schedule(hour, minute),
        inbox_path=str(resolved_inbox),
        installed=True,
        enabled=is_launch_agent_loaded(SCHEDULER_LABEL),
    )


def enable_scheduler(config: AppConfig) -> SchedulerResult:
    settings = load_project_settings(config)
    scheduler = settings.scheduler
    if scheduler is None:
        return SchedulerResult(
            status="missing",
            message="No scheduler configuration found. Run `pop scheduler install` first.",
        )

    plist_path = Path(scheduler.plist_path)
    if not plist_path.exists():
        return SchedulerResult(
            status="missing",
            message=f"LaunchAgent plist not found at {plist_path}. Run `pop scheduler install` again.",
            plist_path=plist_path,
            scheduled_time=_format_schedule(scheduler.hour, scheduler.minute),
            inbox_path=scheduler.inbox_path,
        )

    domain = launchctl_domain()
    if is_launch_agent_loaded(scheduler.label):
        run_launchctl(["bootout", domain, str(plist_path)])
    result = run_launchctl(["bootstrap", domain, str(plist_path)])
    if result.returncode != 0:
        return SchedulerResult(
            status="error",
            message=result.stderr.strip() or "launchctl bootstrap failed.",
            plist_path=plist_path,
            scheduled_time=_format_schedule(scheduler.hour, scheduler.minute),
            inbox_path=scheduler.inbox_path,
            installed=True,
            enabled=False,
        )

    return SchedulerResult(
        status="enabled",
        message="Scheduler enabled.",
        plist_path=plist_path,
        scheduled_time=_format_schedule(scheduler.hour, scheduler.minute),
        inbox_path=scheduler.inbox_path,
        installed=True,
        enabled=True,
    )


def disable_scheduler(config: AppConfig) -> SchedulerResult:
    settings = load_project_settings(config)
    scheduler = settings.scheduler
    if scheduler is None:
        return SchedulerResult(
            status="missing",
            message="No scheduler configuration found.",
        )

    plist_path = Path(scheduler.plist_path)
    if not plist_path.exists():
        return SchedulerResult(
            status="disabled",
            message="Scheduler is already disabled or the plist was removed.",
            plist_path=plist_path,
            scheduled_time=_format_schedule(scheduler.hour, scheduler.minute),
            inbox_path=scheduler.inbox_path,
            installed=False,
            enabled=False,
        )

    domain = launchctl_domain()
    result = run_launchctl(["bootout", domain, str(plist_path)])
    if result.returncode != 0 and is_launch_agent_loaded(scheduler.label):
        return SchedulerResult(
            status="error",
            message=result.stderr.strip() or "launchctl bootout failed.",
            plist_path=plist_path,
            scheduled_time=_format_schedule(scheduler.hour, scheduler.minute),
            inbox_path=scheduler.inbox_path,
            installed=True,
            enabled=True,
        )

    return SchedulerResult(
        status="disabled",
        message="Scheduler disabled.",
        plist_path=plist_path,
        scheduled_time=_format_schedule(scheduler.hour, scheduler.minute),
        inbox_path=scheduler.inbox_path,
        installed=True,
        enabled=False,
    )


def scheduler_status(config: AppConfig) -> SchedulerResult:
    settings = load_project_settings(config)
    scheduler = settings.scheduler
    if scheduler is None:
        return SchedulerResult(
            status="missing",
            message="No scheduler configuration found. Run `pop scheduler install` first.",
        )

    plist_path = Path(scheduler.plist_path)
    installed = plist_path.exists()
    enabled = is_launch_agent_loaded(scheduler.label) if installed else False
    return SchedulerResult(
        status="loaded" if enabled else "installed" if installed else "missing",
        message="Scheduler status loaded.",
        plist_path=plist_path,
        scheduled_time=_format_schedule(scheduler.hour, scheduler.minute),
        inbox_path=scheduler.inbox_path,
        installed=installed,
        enabled=enabled,
    )


def format_scheduler_result(result: SchedulerResult) -> str:
    lines = [result.message]
    if result.plist_path is None:
        return "\n".join(lines)
    lines.extend(
        [
            f"plist_path: {result.plist_path}",
            f"label: {result.label}",
            f"scheduled_time: {result.scheduled_time or 'unknown'}",
            f"inbox_path: {result.inbox_path or 'unknown'}",
            f"installed: {'yes' if result.installed else 'no'}",
            f"enabled: {'yes' if result.enabled else 'no'}",
        ]
    )
    return "\n".join(lines)


def build_launch_agent_plist(
    *,
    config: AppConfig,
    label: str,
    hour: int,
    minute: int,
    command_args: list[str],
    stdout_log_path: Path,
    stderr_log_path: Path,
) -> dict:
    return {
        "Label": label,
        "ProgramArguments": command_args,
        "WorkingDirectory": str(config.root_dir),
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "RunAtLoad": False,
        "StandardOutPath": str(stdout_log_path),
        "StandardErrorPath": str(stderr_log_path),
    }


def resolve_workflow_command(config: AppConfig) -> tuple[str, list[str]]:
    venv_pop = config.root_dir / ".venv" / "bin" / "pop"
    if venv_pop.exists():
        return str(venv_pop), [str(venv_pop), "workflow", "daily"]
    installed_pop = shutil.which("pop")
    if installed_pop:
        return installed_pop, [installed_pop, "workflow", "daily"]
    return sys.executable, [sys.executable, "-m", "pop_cockpit.cli", "workflow", "daily"]


def run_launchctl(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["launchctl", *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            ["launchctl", *arguments],
            returncode=1,
            stdout="",
            stderr="launchctl is not available on this system.",
        )


def is_launch_agent_loaded(label: str) -> bool:
    result = run_launchctl(["print", f"{launchctl_domain()}/{label}"])
    return result.returncode == 0


def launchctl_domain() -> str:
    return f"gui/{os.getuid()}"


def launch_agent_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{SCHEDULER_LABEL}.plist"


def _validate_schedule(hour: int, minute: int) -> None:
    if not 0 <= hour <= 23:
        raise ValueError("--hour must be between 0 and 23.")
    if not 0 <= minute <= 59:
        raise ValueError("--minute must be between 0 and 59.")


def _format_schedule(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"
