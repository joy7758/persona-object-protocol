from __future__ import annotations

import json
import os
import plistlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from pop_cockpit.config import AppConfig

AUTOSTART_LABEL = "com.zhangbin.pop.cockpit"


@dataclass(slots=True)
class AutostartStatus:
    status: str
    message: str
    plist_path: Path
    label: str = AUTOSTART_LABEL
    installed: bool = False
    enabled: bool = False
    last_run_at: str = ""


def build_autostart_plist(
    *,
    config: AppConfig,
    label: str,
    command_args: list[str],
    stdout_log_path: Path,
    stderr_log_path: Path,
) -> dict:
    return {
        "Label": label,
        "ProgramArguments": command_args,
        "WorkingDirectory": str(config.root_dir),
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(stdout_log_path),
        "StandardErrorPath": str(stderr_log_path),
    }


def enable_autostart(config: AppConfig) -> AutostartStatus:
    config.ensure_directories()
    plist_path = autostart_plist_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    _command_path, command_args = resolve_start_command(config)
    stdout_log_path = config.logs_dir / "autostart.stdout.log"
    stderr_log_path = config.logs_dir / "autostart.stderr.log"
    payload = build_autostart_plist(
        config=config,
        label=AUTOSTART_LABEL,
        command_args=command_args,
        stdout_log_path=stdout_log_path,
        stderr_log_path=stderr_log_path,
    )
    with plist_path.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=True)

    domain = launchctl_domain()
    if is_autostart_loaded(AUTOSTART_LABEL):
        run_launchctl(["bootout", domain, str(plist_path)])
    result = run_launchctl(["bootstrap", domain, str(plist_path)])
    enabled = result.returncode == 0 and is_autostart_loaded(AUTOSTART_LABEL)
    if not enabled:
        return AutostartStatus(
            status="error",
            message=result.stderr.strip() or "launchctl bootstrap failed.",
            plist_path=plist_path,
            installed=True,
            enabled=False,
            last_run_at=read_last_startup_timestamp(config) or "",
        )
    return AutostartStatus(
        status="enabled",
        message="Autostart enabled.",
        plist_path=plist_path,
        installed=True,
        enabled=True,
        last_run_at=read_last_startup_timestamp(config) or "",
    )


def disable_autostart(config: AppConfig) -> AutostartStatus:
    plist_path = autostart_plist_path()
    if not plist_path.exists():
        return AutostartStatus(
            status="disabled",
            message="Autostart is already disabled.",
            plist_path=plist_path,
            installed=False,
            enabled=False,
            last_run_at=read_last_startup_timestamp(config) or "",
        )
    result = run_launchctl(["bootout", launchctl_domain(), str(plist_path)])
    if result.returncode != 0 and is_autostart_loaded(AUTOSTART_LABEL):
        return AutostartStatus(
            status="error",
            message=result.stderr.strip() or "launchctl bootout failed.",
            plist_path=plist_path,
            installed=True,
            enabled=True,
            last_run_at=read_last_startup_timestamp(config) or "",
        )
    return AutostartStatus(
        status="disabled",
        message="Autostart disabled.",
        plist_path=plist_path,
        installed=True,
        enabled=False,
        last_run_at=read_last_startup_timestamp(config) or "",
    )


def autostart_status(config: AppConfig) -> AutostartStatus:
    plist_path = autostart_plist_path()
    installed = plist_path.exists()
    enabled = is_autostart_loaded(AUTOSTART_LABEL) if installed else False
    return AutostartStatus(
        status="enabled" if enabled else "installed" if installed else "missing",
        message="Autostart status loaded.",
        plist_path=plist_path,
        installed=installed,
        enabled=enabled,
        last_run_at=read_last_startup_timestamp(config) or "",
    )


def format_autostart_status(result: AutostartStatus) -> str:
    return "\n".join(
        [
            result.message,
            f"plist_path: {result.plist_path}",
            f"label: {result.label}",
            f"installed: {'yes' if result.installed else 'no'}",
            f"enabled: {'yes' if result.enabled else 'no'}",
            f"last_run_at: {result.last_run_at or 'unknown'}",
        ]
    )


def resolve_start_command(config: AppConfig) -> tuple[str, list[str]]:
    venv_pop = config.root_dir / ".venv" / "bin" / "pop"
    if venv_pop.exists():
        return str(venv_pop), [str(venv_pop), "start"]
    installed_pop = shutil.which("pop")
    if installed_pop:
        return installed_pop, [installed_pop, "start"]
    return sys.executable, [sys.executable, "-m", "pop_cockpit.cli", "start"]


def read_last_startup_timestamp(config: AppConfig) -> str | None:
    log_path = config.logs_dir / "startup.log"
    if not log_path.exists():
        return None
    for line in reversed(log_path.read_text(encoding="utf-8").splitlines()):
        candidate = line.strip()
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        timestamp = payload.get("timestamp")
        if isinstance(timestamp, str) and timestamp:
            return timestamp
    return None


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


def is_autostart_loaded(label: str) -> bool:
    result = run_launchctl(["print", f"{launchctl_domain()}/{label}"])
    return result.returncode == 0


def launchctl_domain() -> str:
    return f"gui/{os.getuid()}"


def autostart_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{AUTOSTART_LABEL}.plist"
