from __future__ import annotations

from typing import Any

from pop.models import PersonaObject


class PersonaValidationError(ValueError):
    """Raised when a POP persona object fails minimal semantic validation."""


def _require_non_empty_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PersonaValidationError(f"`{field_name}` must be a non-empty string.")


def _require_string_list(value: Any, field_name: str) -> None:
    if not isinstance(value, list):
        raise PersonaValidationError(f"`{field_name}` must be a list.")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise PersonaValidationError(
                f"`{field_name}` item {index} must be a non-empty string."
            )


def validate_persona_dict(data: dict) -> None:
    if not isinstance(data, dict):
        raise PersonaValidationError("Persona payload must be a JSON object.")

    for field_name in ("id", "version", "name", "summary"):
        _require_non_empty_string(data.get(field_name), field_name)

    for field_name in (
        "traits",
        "communication_style",
        "task_orientation",
        "boundaries",
        "preferred_outputs",
    ):
        _require_string_list(data.get(field_name), field_name)

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        raise PersonaValidationError("`metadata` must be a dict.")


def validate_persona(persona: PersonaObject) -> None:
    validate_persona_dict(persona.to_dict())
