from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Persona:
    def __init__(self, data: dict[str, Any]) -> None:
        self.name = data.get("name")
        self.role = data.get("role")
        self.description = data.get("description")
        self.skills = data.get("skills", [])
        self.tools = data.get("preferred_tools", [])

    def summary(self) -> str:
        return f"{self.name} ({self.role})"


def load_persona(path: str | Path) -> Persona:
    persona_path = Path(path)
    with persona_path.open(encoding="utf-8") as file:
        data = json.load(file)
    return Persona(data)


def load_all_personas(
    folder: str | Path = "personas",
    names: list[str] | None = None,
) -> list[Persona]:
    folder_path = Path(folder)
    persona_paths = sorted(folder_path.glob("*.json"))
    if names is not None:
        persona_paths = [folder_path / name for name in names]
    return [load_persona(path) for path in persona_paths]
