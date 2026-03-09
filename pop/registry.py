from pathlib import Path
from typing import List, Optional

from .loader import load_persona, validate_persona


PERSONA_DIR = Path("personas")
POP_ID_PREFIX = "pop:"


def normalize_persona_ref(persona_ref: str) -> str:
    """
    Normalize a POP persona reference.

    Supported inputs:
    - marketing_manager_v1
    - pop:marketing_manager_v1
    """
    if persona_ref.startswith(POP_ID_PREFIX):
        return persona_ref[len(POP_ID_PREFIX) :]
    return persona_ref


def _iter_persona_files():
    if not PERSONA_DIR.exists():
        return []
    return sorted(PERSONA_DIR.glob("*.json"))


def list_personas() -> List[str]:
    """
    List available persona file paths in the local registry.
    """
    return [str(path) for path in _iter_persona_files()]


def list_persona_ids() -> List[str]:
    """
    List normalized persona IDs from local registry files.
    """
    ids: List[str] = []
    for path in _iter_persona_files():
        persona = load_persona(path)
        ids.append(persona.persona_id)
    return ids


def resolve_persona(persona_ref: str) -> Optional[Path]:
    """
    Resolve persona reference to a file path.

    Resolution order:
    1. Match normalized ref against persona.persona_id
    2. Fallback to filename stem match
    """
    normalized = normalize_persona_ref(persona_ref)

    for path in _iter_persona_files():
        persona = load_persona(path)
        if persona.persona_id == normalized:
            return path

    fallback = PERSONA_DIR / f"{normalized}.json"
    if fallback.exists():
        return fallback

    return None


def load_persona_by_id(persona_ref: str):
    """
    Load persona by normalized POP persona reference.
    """
    path = resolve_persona(persona_ref)
    if path is None:
        raise ValueError(f"Persona not found: {persona_ref}")

    persona = load_persona(path)
    validate_persona(path)

    return persona
