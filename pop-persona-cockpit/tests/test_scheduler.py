import plistlib
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from pop_cockpit import cli as cli_module
from pop_cockpit.config import AppConfig
from pop_cockpit.scheduler import (
    SCHEDULER_LABEL,
    build_launch_agent_plist,
    disable_scheduler,
    enable_scheduler,
    format_scheduler_result,
    install_scheduler,
    scheduler_status,
)
from pop_cockpit.settings import load_project_settings
from pop_cockpit.storage import ensure_runtime

runner = CliRunner()


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


def test_scheduler_plist_generation(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    plist_payload = build_launch_agent_plist(
        config=config,
        label=SCHEDULER_LABEL,
        hour=22,
        minute=30,
        command_args=["/tmp/pop", "workflow", "daily"],
        stdout_log_path=config.logs_dir / "scheduler.stdout.log",
        stderr_log_path=config.logs_dir / "scheduler.stderr.log",
    )

    assert plist_payload["Label"] == SCHEDULER_LABEL
    assert plist_payload["ProgramArguments"] == ["/tmp/pop", "workflow", "daily"]
    assert plist_payload["StartCalendarInterval"] == {"Hour": 22, "Minute": 30}
    assert plist_payload["StandardOutPath"].endswith("scheduler.stdout.log")


def test_scheduler_install_persists_config_and_writes_plist(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    launch_agents_dir = tmp_path / "LaunchAgents"
    monkeypatch.setattr("pop_cockpit.scheduler.launch_agent_plist_path", lambda: launch_agents_dir / f"{SCHEDULER_LABEL}.plist")
    monkeypatch.setattr(
        "pop_cockpit.scheduler.run_launchctl",
        lambda arguments: subprocess.CompletedProcess(["launchctl", *arguments], 1, "", "not loaded"),
    )
    inbox = tmp_path / "inbox"

    result = install_scheduler(config, hour=22, minute=30, inbox_path=inbox)

    assert result.status == "installed"
    assert result.plist_path is not None and result.plist_path.exists()
    plist_payload = plistlib.loads(result.plist_path.read_bytes())
    assert plist_payload["Label"] == SCHEDULER_LABEL
    settings = load_project_settings(config)
    assert settings.inbox_path == str(inbox.resolve())
    assert settings.scheduler is not None
    assert settings.scheduler.hour == 22
    assert settings.scheduler.minute == 30


def test_scheduler_enable_disable_and_status_are_testable(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    launch_agents_dir = tmp_path / "LaunchAgents"
    plist_path = launch_agents_dir / f"{SCHEDULER_LABEL}.plist"
    inbox = tmp_path / "inbox"
    state = {"loaded": False}

    def fake_launchctl(arguments: list[str]) -> subprocess.CompletedProcess[str]:
        command = arguments[0]
        if command == "print":
            return subprocess.CompletedProcess(
                ["launchctl", *arguments],
                0 if state["loaded"] else 1,
                "loaded" if state["loaded"] else "",
                "" if state["loaded"] else "not loaded",
            )
        if command == "bootstrap":
            state["loaded"] = True
            return subprocess.CompletedProcess(["launchctl", *arguments], 0, "", "")
        if command == "bootout":
            state["loaded"] = False
            return subprocess.CompletedProcess(["launchctl", *arguments], 0, "", "")
        return subprocess.CompletedProcess(["launchctl", *arguments], 1, "", "unexpected")

    monkeypatch.setattr("pop_cockpit.scheduler.launch_agent_plist_path", lambda: plist_path)
    monkeypatch.setattr("pop_cockpit.scheduler.run_launchctl", fake_launchctl)
    install_scheduler(config, hour=22, minute=30, inbox_path=inbox)

    enabled = enable_scheduler(config)
    status = scheduler_status(config)
    disabled = disable_scheduler(config)

    assert enabled.status == "enabled"
    assert status.enabled is True
    assert disabled.status == "disabled"
    assert disable_scheduler(config).enabled is False


def test_scheduler_status_cli_output(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    launch_agents_dir = tmp_path / "LaunchAgents"
    plist_path = launch_agents_dir / f"{SCHEDULER_LABEL}.plist"
    inbox = tmp_path / "inbox"
    monkeypatch.setattr("pop_cockpit.scheduler.launch_agent_plist_path", lambda: plist_path)
    monkeypatch.setattr(
        "pop_cockpit.scheduler.run_launchctl",
        lambda arguments: subprocess.CompletedProcess(["launchctl", *arguments], 1, "", "not loaded"),
    )
    install_scheduler(config, hour=21, minute=15, inbox_path=inbox)
    monkeypatch.setattr(cli_module, "_config", lambda: config)

    result = runner.invoke(cli_module.app, ["scheduler", "status"])

    assert result.exit_code == 0
    assert "plist_path:" in result.stdout
    assert "scheduled_time: 21:15" in result.stdout
    assert "enabled: no" in result.stdout


def test_scheduler_summary_output_is_readable(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    launch_agents_dir = tmp_path / "LaunchAgents"
    plist_path = launch_agents_dir / f"{SCHEDULER_LABEL}.plist"
    inbox = tmp_path / "inbox"
    monkeypatch.setattr("pop_cockpit.scheduler.launch_agent_plist_path", lambda: plist_path)
    monkeypatch.setattr(
        "pop_cockpit.scheduler.run_launchctl",
        lambda arguments: subprocess.CompletedProcess(["launchctl", *arguments], 1, "", "not loaded"),
    )

    result = install_scheduler(config, hour=22, minute=30, inbox_path=inbox)
    summary = format_scheduler_result(result)

    assert "plist_path:" in summary
    assert "label:" in summary
    assert "installed: yes" in summary
