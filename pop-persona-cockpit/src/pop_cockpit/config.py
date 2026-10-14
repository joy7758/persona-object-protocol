from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    root_dir: Path
    data_dir: Path
    raw_logs_dir: Path
    daily_notes_dir: Path
    persona_core_dir: Path
    sessions_dir: Path
    database_path: Path

    @classmethod
    def load(cls) -> "AppConfig":
        root_dir = Path(__file__).resolve().parents[2]
        data_dir = root_dir / "data"
        return cls(
            root_dir=root_dir,
            data_dir=data_dir,
            raw_logs_dir=data_dir / "raw_logs",
            daily_notes_dir=data_dir / "daily_notes",
            persona_core_dir=data_dir / "persona_core",
            sessions_dir=data_dir / "sessions",
            database_path=data_dir / "pop_persona.db",
        )

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.raw_logs_dir,
            self.daily_notes_dir,
            self.persona_core_dir,
            self.sessions_dir,
            self.logs_dir,
            self.execution_dir,
            self.sync_local_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def settings_path(self) -> Path:
        return self.data_dir / "settings.json"

    @property
    def execution_dir(self) -> Path:
        return self.data_dir / "execution"

    @property
    def sync_local_dir(self) -> Path:
        return self.data_dir / "sync"

    @property
    def sync_secret_path(self) -> Path:
        return self.sync_local_dir / "secret.json"

    @property
    def sync_state_path(self) -> Path:
        return self.sync_local_dir / "state.json"

    @property
    def sync_history_path(self) -> Path:
        return self.sync_local_dir / "history.jsonl"
