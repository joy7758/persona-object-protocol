import plistlib
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from pop_cockpit import cli as cli_module
from pop_cockpit.autostart import (
    AUTOSTART_LABEL,
    autostart_status,
    build_autostart_plist,
    disable_autostart,
    enable_autostart,
    format_autostart_status,
)
from pop_cockpit.config import AppConfig
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


def test_autostart_plist_generation(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    payload = build_autostart_plist(
        config=config,
        label=AUTOSTART_LABEL,
        command_args=["/tmp/pop", "start"],
        stdout_log_path=config.logs_dir / "autostart.stdout.log",
        stderr_log_path=config.logs_dir / "autostart.stderr.log",
    )

    assert payload["Label"] == AUTOSTART_LABEL
    assert payload["ProgramArguments"] == ["/tmp/pop", "start"]
    assert payload["RunAtLoad"] is True
    assert payload["KeepAlive"] is True
    assert payload["StandardOutPath"].endswith("autostart.stdout.log")


def test_autostart_enable_disable_and_status_are_testable(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    launch_agents_dir = tmp_path / "LaunchAgents"
    plist_path = launch_agents_dir / f"{AUTOSTART_LABEL}.plist"
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

    monkeypatch.setattr("pop_cockpit.autostart.autostart_plist_path", lambda: plist_path)
    monkeypatch.setattr("pop_cockpit.autostart.run_launchctl", fake_launchctl)

    enabled = enable_autostart(config)
    status = autostart_status(config)
    disabled = disable_autostart(config)

    assert enabled.status == "enabled"
    assert plist_path.exists()
    plist_payload = plistlib.loads(plist_path.read_bytes())
    assert plist_payload["Label"] == AUTOSTART_LABEL
    assert status.enabled is True
    assert disabled.status == "disabled"


def test_autostart_status_cli_output(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    launch_agents_dir = tmp_path / "LaunchAgents"
    plist_path = launch_agents_dir / f"{AUTOSTART_LABEL}.plist"
    monkeypatch.setattr("pop_cockpit.autostart.autostart_plist_path", lambda: plist_path)
    monkeypatch.setattr(
        "pop_cockpit.autostart.run_launchctl",
        lambda arguments: subprocess.CompletedProcess(["launchctl", *arguments], 1, "", "not loaded"),
    )

    enable_autostart(config)
    monkeypatch.setattr(cli_module, "_config", lambda: config)

    result = runner.invoke(cli_module.app, ["autostart", "status"])

    assert result.exit_code == 0
    assert "plist_path:" in result.stdout
    assert "label: com.zhangbin.pop.cockpit" in result.stdout
    assert "enabled: no" in result.stdout


def test_autostart_summary_output_is_readable(tmp_path: Path, monkeypatch) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    launch_agents_dir = tmp_path / "LaunchAgents"
    plist_path = launch_agents_dir / f"{AUTOSTART_LABEL}.plist"
    monkeypatch.setattr("pop_cockpit.autostart.autostart_plist_path", lambda: plist_path)
    monkeypatch.setattr(
        "pop_cockpit.autostart.run_launchctl",
        lambda arguments: subprocess.CompletedProcess(["launchctl", *arguments], 1, "", "not loaded"),
    )

    result = enable_autostart(config)
    summary = format_autostart_status(result)

    assert "plist_path:" in summary
    assert "installed: yes" in summary
    assert "enabled:" in summary
