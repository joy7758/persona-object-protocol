from __future__ import annotations

import json

from pop_cockpit.config import AppConfig
from pop_cockpit.schemas import ProjectSettings
from pop_cockpit.utils import write_json


def load_project_settings(config: AppConfig) -> ProjectSettings:
    if not config.settings_path.exists():
        return ProjectSettings()
    payload = json.loads(config.settings_path.read_text(encoding="utf-8"))
    return ProjectSettings.model_validate(payload)


def save_project_settings(config: AppConfig, settings: ProjectSettings) -> None:
    write_json(config.settings_path, settings.model_dump(mode="json"))
