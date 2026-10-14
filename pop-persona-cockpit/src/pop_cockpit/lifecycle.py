from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

import uvicorn

from pop_cockpit.config import AppConfig
from pop_cockpit.settings import load_project_settings
from pop_cockpit.sync import start_sync_worker, stop_sync_worker
from pop_cockpit.utils import utc_now
from pop_cockpit.webapp import create_app

POP_HOST = "127.0.0.1"
POP_PORT = 8765
POP_URL = f"http://{POP_HOST}:{POP_PORT}"


def open_local_browser(url: str = POP_URL) -> bool:
    result = subprocess.run(
        ["open", url],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def check_backend_health(url: str = POP_URL) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(f"{url}/api/capture/status", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return False, str(exc)
    if not payload.get("backend_alive", False):
        return False, "backend reported not alive"
    return True, "ok"


def run_pop_service(
    config: AppConfig,
    *,
    auto_open_browser: bool | None = None,
    health_interval_seconds: int = 10,
    max_restart_attempts: int = 3,
    health_check_fn: Callable[[str], tuple[bool, str]] | None = None,
    open_browser_fn: Callable[[str], bool] | None = None,
    server_factory: Callable[[AppConfig], Any] | None = None,
) -> None:
    config.ensure_directories()
    settings = load_project_settings(config)
    should_open_browser = (
        settings.auto_open_browser if auto_open_browser is None else auto_open_browser
    )
    health_check = health_check_fn or check_backend_health
    browser_opener = open_browser_fn or open_local_browser
    build_server = server_factory or _default_server_factory
    startup_log_path = config.logs_dir / "startup.log"
    health_log_path = config.logs_dir / "health.log"

    restart_attempts = 0
    consecutive_failures = 0
    browser_opened = False
    monitoring_enabled = True

    sync_worker = start_sync_worker(config)
    server, server_thread = _start_server(build_server(config))
    _append_json_log(
        startup_log_path,
        {
            "timestamp": utc_now().isoformat(),
            "event": "start",
            "url": POP_URL,
            "restart_attempt": restart_attempts,
        },
    )

    try:
        browser_opened = _maybe_open_browser(
            should_open_browser,
            browser_opener,
            health_check,
            browser_opened,
        )
        while True:
            if not server_thread.is_alive():
                if restart_attempts >= max_restart_attempts:
                    _append_json_log(
                        health_log_path,
                        {
                            "timestamp": utc_now().isoformat(),
                            "event": "restart_limit_reached",
                            "detail": "server thread stopped",
                        },
                    )
                    break
                restart_attempts += 1
                _append_json_log(
                    health_log_path,
                    {
                        "timestamp": utc_now().isoformat(),
                        "event": "thread_stopped_restart",
                        "restart_attempt": restart_attempts,
                    },
                )
                server, server_thread = _start_server(build_server(config))
                _append_json_log(
                    startup_log_path,
                    {
                        "timestamp": utc_now().isoformat(),
                        "event": "restart",
                        "url": POP_URL,
                        "restart_attempt": restart_attempts,
                    },
                )
                browser_opened = _maybe_open_browser(
                    should_open_browser,
                    browser_opener,
                    health_check,
                    browser_opened,
                )
                continue

            time.sleep(health_interval_seconds)
            if not monitoring_enabled:
                continue

            healthy, detail = health_check(POP_URL)
            if healthy:
                consecutive_failures = 0
                browser_opened = _maybe_open_browser(
                    should_open_browser,
                    browser_opener,
                    health_check,
                    browser_opened,
                )
                continue

            consecutive_failures += 1
            _append_json_log(
                health_log_path,
                {
                    "timestamp": utc_now().isoformat(),
                    "event": "health_check_failed",
                    "detail": detail,
                    "consecutive_failures": consecutive_failures,
                },
            )
            if consecutive_failures < 3:
                continue

            if restart_attempts >= max_restart_attempts:
                _append_json_log(
                    health_log_path,
                    {
                        "timestamp": utc_now().isoformat(),
                        "event": "restart_limit_reached",
                        "detail": detail,
                        "consecutive_failures": consecutive_failures,
                    },
                )
                monitoring_enabled = False
                _stop_server(server, server_thread)
                break

            restart_attempts += 1
            _append_json_log(
                health_log_path,
                {
                    "timestamp": utc_now().isoformat(),
                    "event": "soft_restart",
                    "detail": detail,
                    "restart_attempt": restart_attempts,
                },
            )
            _stop_server(server, server_thread)
            server, server_thread = _start_server(build_server(config))
            _append_json_log(
                startup_log_path,
                {
                    "timestamp": utc_now().isoformat(),
                    "event": "restart",
                    "url": POP_URL,
                    "restart_attempt": restart_attempts,
                },
            )
            consecutive_failures = 0
    except KeyboardInterrupt:
        _stop_server(server, server_thread)
        stop_sync_worker(sync_worker)
        raise
    finally:
        stop_sync_worker(sync_worker)


def _default_server_factory(config: AppConfig) -> uvicorn.Server:
    return uvicorn.Server(
        uvicorn.Config(
            create_app(config),
            host=POP_HOST,
            port=POP_PORT,
            log_level="info",
        )
    )


def _start_server(server: Any) -> tuple[Any, threading.Thread]:
    thread = threading.Thread(target=server.run, daemon=True, name="pop-web-server")
    thread.start()
    return server, thread


def _stop_server(server: Any, thread: threading.Thread) -> None:
    setattr(server, "should_exit", True)
    setattr(server, "force_exit", True)
    thread.join(timeout=5)


def _append_json_log(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _maybe_open_browser(
    should_open_browser: bool,
    browser_opener: Callable[[str], bool],
    health_check: Callable[[str], tuple[bool, str]],
    browser_opened: bool,
) -> bool:
    if browser_opened or not should_open_browser:
        return browser_opened
    for _ in range(20):
        healthy, _detail = health_check(POP_URL)
        if healthy:
            browser_opener(POP_URL)
            return True
        time.sleep(0.5)
    return browser_opened
