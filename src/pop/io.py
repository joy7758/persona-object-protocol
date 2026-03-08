from __future__ import annotations

import json
from pathlib import Path

from pop.models import PersonaObject


def load_persona(path: str | Path) -> PersonaObject:
    file_path = Path(path).expanduser()
    try:
        raw = file_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"POP persona file not found: {file_path}") from exc
    except OSError as exc:
        raise OSError(f"Unable to read POP persona file: {file_path}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in POP persona file {file_path}: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"POP persona file must contain a JSON object: {file_path}")

    return PersonaObject.from_dict(data)


def save_persona(persona: PersonaObject, path: str | Path) -> None:
    file_path = Path(path).expanduser()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(persona.to_dict(), indent=2, ensure_ascii=False) + "\n"
    try:
        file_path.write_text(payload, encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Unable to write POP persona file: {file_path}") from exc
