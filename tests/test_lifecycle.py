import time
from pathlib import Path

import pytest

from pop_cockpit.config import AppConfig
from pop_cockpit.lifecycle import check_backend_health, run_pop_service
from pop_cockpit.schemas import ProjectSettings
from pop_cockpit.settings import load_project_settings, save_project_settings
from pop_cockpit.storage import ensure_runtime


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


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeServer:
    def __init__(self) -> None:
        self.should_exit = False
        self.force_exit = False

    def run(self) -> None:
        while not self.should_exit:
            time.sleep(0.01)


def test_auto_open_browser_setting_persists(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    save_project_settings(config, ProjectSettings(auto_open_browser=False))

    settings = load_project_settings(config)

    assert settings.auto_open_browser is False


def test_health_check_logic_handles_success_and_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda url, timeout: _FakeResponse(b'{"backend_alive": true}'),
    )
    healthy, message = check_backend_health("http://127.0.0.1:8765")
    assert healthy is True
    assert message == "ok"

    def raise_error(url, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", raise_error)
    healthy, message = check_backend_health("http://127.0.0.1:8765")
    assert healthy is False
    assert "connection refused" in message


def test_run_pop_service_soft_restarts_after_repeated_failures(tmp_path: Path) -> None:
    config = make_test_config(tmp_path)
    ensure_runtime(config)
    save_project_settings(config, ProjectSettings(auto_open_browser=True))

    factory_calls: list[_FakeServer] = []
    browser_open_calls: list[str] = []
    health_calls = {"count": 0}

    def fake_server_factory(_config: AppConfig) -> _FakeServer:
        server = _FakeServer()
        factory_calls.append(server)
        return server

    def fake_health_check(url: str) -> tuple[bool, str]:
        health_calls["count"] += 1
        if health_calls["count"] == 1:
            return True, "ok"
        if health_calls["count"] in {2, 3, 4}:
            return False, "down"
        raise KeyboardInterrupt

    def fake_open_browser(url: str) -> bool:
        browser_open_calls.append(url)
        return True

    with pytest.raises(KeyboardInterrupt):
        run_pop_service(
            config,
            health_interval_seconds=0.01,
            max_restart_attempts=3,
            health_check_fn=fake_health_check,
            open_browser_fn=fake_open_browser,
            server_factory=fake_server_factory,
        )

    assert len(factory_calls) >= 2
    assert browser_open_calls == ["http://127.0.0.1:8765"]
    health_log = config.logs_dir / "health.log"
    assert health_log.exists()
    assert "soft_restart" in health_log.read_text(encoding="utf-8")
