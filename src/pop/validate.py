from __future__ import annotations

from importlib import import_module
from typing import Any

from pop.models import PersonaObject
from pop.schema import load_pop_schema


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


def _load_jsonschema_components() -> tuple[Any, Any, Any]:
    try:
        exceptions = import_module("jsonschema.exceptions")
        validators = import_module("jsonschema.validators")
    except ImportError as exc:
        raise PersonaValidationError(
            "Strict JSON Schema validation requires the optional `schema` dependency. "
            "Install it with `pip install -e '.[schema]'`."
        ) from exc

    return (
        validators.validator_for,
        exceptions.ValidationError,
        exceptions.SchemaError,
    )


def _format_jsonschema_error(error: Any) -> str:
    path_parts = [str(part) for part in getattr(error, "absolute_path", [])]
    if path_parts:
        return f"{'.'.join(path_parts)}: {error.message}"
    return str(error.message)


def validate_persona_schema_dict(data: dict) -> None:
    if not isinstance(data, dict):
        raise PersonaValidationError("Persona payload must be a JSON object.")

    validator_for, validation_error_cls, schema_error_cls = _load_jsonschema_components()
    schema = load_pop_schema()
    validator_cls = validator_for(schema)

    try:
        validator_cls.check_schema(schema)
        validator = validator_cls(schema)
        validator.validate(data)
    except schema_error_cls as exc:
        raise PersonaValidationError(f"POP schema is invalid: {exc.message}") from exc
    except validation_error_cls as exc:
        raise PersonaValidationError(_format_jsonschema_error(exc)) from exc


def validate_persona_schema(persona: PersonaObject) -> None:
    validate_persona_schema_dict(persona.to_dict())
