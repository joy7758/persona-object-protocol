import json
from pathlib import Path

from .loader import load_persona


DEFAULT_PERSONA_DIR = Path("personas")


def list_personas(persona_dir=DEFAULT_PERSONA_DIR):
    persona_dir = Path(persona_dir)
    if not persona_dir.exists():
        return []

    return sorted(str(path) for path in persona_dir.glob("*.json") if path.is_file())


def resolve_persona(persona_id, persona_dir=DEFAULT_PERSONA_DIR):
    persona_dir = Path(persona_dir)

    for path in persona_dir.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if data.get("persona_id") == persona_id:
            return str(path)

    return None


def load_persona_by_id(persona_id, persona_dir=DEFAULT_PERSONA_DIR):
    path = resolve_persona(persona_id, persona_dir=persona_dir)
    if path is None:
        raise FileNotFoundError(f"Persona not found for persona_id={persona_id!r}")
    return load_persona(path)
