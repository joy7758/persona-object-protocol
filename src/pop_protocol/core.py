from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
V1_SCHEMA_PATH = ROOT / "schema" / "pop.schema.json"
LEGACY_SCHEMA_PATH = ROOT / "schema" / "persona.schema.json"
V1_STATUSES = {"draft", "active", "deprecated", "replaced", "revoked"}


@dataclass
class ValidationReport:
    schema_kind: str
    schema_path: str
    schema_errors: list[str]
    lifecycle_errors: list[str]
    boundary_errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not (self.schema_errors or self.lifecycle_errors or self.boundary_errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_kind": self.schema_kind,
            "schema_path": self.schema_path,
            "ok": self.ok,
            "schema_errors": self.schema_errors,
            "lifecycle_errors": self.lifecycle_errors,
            "boundary_errors": self.boundary_errors,
            "warnings": self.warnings,
        }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_pop(source: str | Path | dict[str, Any], *, allow_legacy: bool = True) -> dict[str, Any]:
    if isinstance(source, dict):
        payload = source
        source_label = None
    else:
        path = resolve_input_path(str(source))
        payload = load_json(path)
        source_label = path.as_posix()

    schema_kind = detect_schema_kind(payload)
    if schema_kind == "v1":
        return payload
    if not allow_legacy:
        raise ValueError("Legacy POP 0.1 objects require allow_legacy=True.")
    return migrate_pop01_object(payload, source_label=source_label)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def repo_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def resolve_input_path(path_arg: str) -> Path:
    path = Path(path_arg).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def detect_schema_kind(payload: dict[str, Any]) -> str:
    if payload.get("kind") == "persona-object":
        return "v1"
    if payload.get("schema_version") == "pop-0.1":
        return "pop-0.1"
    raise ValueError("Unable to detect POP object type. Expected `kind` or `schema_version`.")


def schema_path_for_kind(schema_kind: str) -> Path:
    if schema_kind == "v1":
        return V1_SCHEMA_PATH
    if schema_kind == "pop-0.1":
        return LEGACY_SCHEMA_PATH
    raise ValueError(f"Unsupported schema kind: {schema_kind}")


def _load_jsonschema_validator() -> Any:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise RuntimeError(
            "Schema validation requires the optional `schema` dependency. "
            "Install it with `pip install -e '.[schema]'`."
        ) from exc
    return Draft202012Validator


def load_validator(schema_kind: str) -> Any:
    schema = load_json(schema_path_for_kind(schema_kind))
    validator_cls = _load_jsonschema_validator()
    return validator_cls(schema, format_checker=validator_cls.FORMAT_CHECKER)


def validate_schema_errors(payload: Any, schema_kind: str) -> list[str]:
    validator = load_validator(schema_kind)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    return [error.message for error in errors]


def semantic_validation_v1(payload: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    lifecycle_errors: list[str] = []
    boundary_errors: list[str] = []
    warnings: list[str] = []

    status = payload.get("status")
    provenance = payload.get("provenance", {})
    boundaries = payload.get("boundaries", {})

    if status not in V1_STATUSES:
        lifecycle_errors.append(f"Unsupported lifecycle status `{status}`.")

    if status in {"deprecated", "replaced", "revoked"} and "updated" not in provenance:
        warnings.append(
            f"Status `{status}` is set but provenance.updated is missing; audit trails will be weaker."
        )

    for boundary_name, boundary_value in boundaries.items():
        if isinstance(boundary_value, bool):
            if boundary_value is True:
                warnings.append(
                    f"Boundary `{boundary_name}` is `true`; runtime policy still controls real permissions."
                )
            continue

        decision = boundary_value.get("decision")
        if decision == "allow":
            warnings.append(
                f"Boundary `{boundary_name}` uses `allow`; this does not grant runtime authority on its own."
            )
        if decision == "unspecified" and "reason" not in boundary_value:
            boundary_errors.append(
                f"Boundary `{boundary_name}` is `unspecified` without a reason."
            )

    return lifecycle_errors, boundary_errors, warnings


def semantic_validation_legacy(payload: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    warnings = [
        "Legacy POP 0.1 object detected; migrate to POP v1.0 for canonical validation and interoperability."
    ]
    return [], [], warnings


def validate_object(payload: dict[str, Any], schema_mode: str = "auto") -> ValidationReport:
    schema_kind = detect_schema_kind(payload) if schema_mode == "auto" else schema_mode
    schema_errors = validate_schema_errors(payload, schema_kind)

    lifecycle_errors: list[str] = []
    boundary_errors: list[str] = []
    warnings: list[str] = []

    if not schema_errors:
        if schema_kind == "v1":
            lifecycle_errors, boundary_errors, warnings = semantic_validation_v1(payload)
        else:
            lifecycle_errors, boundary_errors, warnings = semantic_validation_legacy(payload)

    return ValidationReport(
        schema_kind=schema_kind,
        schema_path=repo_rel(schema_path_for_kind(schema_kind)),
        schema_errors=schema_errors,
        lifecycle_errors=lifecycle_errors,
        boundary_errors=boundary_errors,
        warnings=warnings,
    )


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    if not slug:
        slug = "boundary"
    if slug[0].isdigit():
        slug = f"boundary_{slug}"
    return slug


def choose_legacy_role(payload: dict[str, Any]) -> str:
    for anchor in payload.get("anchors", []):
        if anchor.get("type") == "role" and anchor.get("value"):
            return str(anchor["value"])
    return str(payload.get("name", "legacy-persona"))


def boundary_decision_from_text(text: str) -> str:
    normalized = text.lower()
    if "escalat" in normalized or "review" in normalized:
        return "requires-review"
    if "does not" in normalized or "do not" in normalized or "avoid" in normalized:
        return "disallow"
    return "out-of-scope"


def convert_legacy_boundaries(payload: dict[str, Any]) -> dict[str, Any]:
    boundary_texts: list[str] = []
    for anchor in payload.get("anchors", []):
        if anchor.get("type") == "boundary" and anchor.get("value"):
            boundary_texts.append(str(anchor["value"]))
    for entry in payload.get("behavior", {}).get("boundaries", []):
        boundary_texts.append(str(entry))

    converted: dict[str, Any] = {}
    for index, text in enumerate(unique_strings(boundary_texts), start=1):
        key = slugify(text)
        if key in converted:
            key = f"{key}_{index}"
        converted[key] = {
            "decision": boundary_decision_from_text(text),
            "reason": text,
        }

    if not converted:
        converted["legacy_boundary_review"] = {
            "decision": "unspecified",
            "reason": "Legacy POP 0.1 object had no explicit boundary statements.",
        }
    return converted


def migrate_pop01_object(payload: dict[str, Any], source_label: str | None = None) -> dict[str, Any]:
    role = choose_legacy_role(payload)
    traits = unique_strings(
        [
            *payload.get("traits", []),
            payload.get("behavior", {}).get("tone", ""),
        ]
    )
    provenance: dict[str, Any] = {
        "issuer": "pop-migrate-pop01",
        "created": date.today().isoformat(),
        "legacy_source": payload.get("schema_version", "pop-0.1"),
    }
    if source_label:
        provenance["source"] = source_label

    return {
        "kind": "persona-object",
        "id": str(payload["id"]),
        "version": "1.0.0-migrated",
        "role": role,
        "traits": traits or ["legacy-migrated"],
        "boundaries": convert_legacy_boundaries(payload),
        "status": "active",
        "provenance": provenance,
    }


def ensure_v1_object(payload: dict[str, Any], source_label: str | None = None) -> tuple[dict[str, Any], bool]:
    schema_kind = detect_schema_kind(payload)
    if schema_kind == "v1":
        return payload, False
    return migrate_pop01_object(payload, source_label=source_label), True


def render_boundary_text(boundary_name: str, boundary_value: Any) -> str:
    if isinstance(boundary_value, bool):
        state = "not claimed" if boundary_value is False else "not blocked by the persona object"
        return f"{boundary_name}: {state}"

    decision = boundary_value["decision"]
    if decision == "requires-review":
        text = f"{boundary_name}: requires review"
    elif decision in {"disallow", "out-of-scope"}:
        text = f"{boundary_name}: out of scope"
    elif decision == "allow":
        text = f"{boundary_name}: allowed only if runtime policy permits"
    else:
        text = f"{boundary_name}: unspecified"

    reason = boundary_value.get("reason")
    if reason:
        text = f"{text} ({reason})"
    return text


def project_prompt(payload: dict[str, Any]) -> str:
    boundary_text = "; ".join(
        render_boundary_text(name, value) for name, value in payload["boundaries"].items()
    )
    traits = ", ".join(payload["traits"])
    return (
        f"You are a {payload['role']} with traits {traits}. "
        f"Object id: {payload['id']}. Version: {payload['version']}. Status: {payload['status']}. "
        f"Boundaries: {boundary_text}."
    )


def project_app(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "projection_type": "app",
        "role_model": {
            "kind": payload["kind"],
            "id": payload["id"],
            "version": payload["version"],
            "role": payload["role"],
            "traits": payload["traits"],
            "status": payload["status"],
            "boundaries": payload["boundaries"],
            "provenance": payload["provenance"],
        },
    }


def project_agent(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "projection_type": "agent",
        "runtime_contract": {
            "persona_ref": {
                "kind": payload["kind"],
                "id": payload["id"],
                "version": payload["version"],
            },
            "behavior_contract": {
                "role": payload["role"],
                "traits": payload["traits"],
            },
            "boundary_contract": payload["boundaries"],
            "lifecycle": {
                "status": payload["status"],
            },
            "provenance": payload["provenance"],
        },
    }


def project_object(payload: dict[str, Any], runtime: str) -> str | dict[str, Any]:
    if runtime == "prompt":
        return project_prompt(payload)
    if runtime == "app":
        return project_app(payload)
    if runtime == "agent":
        return project_agent(payload)
    raise ValueError(f"Unsupported runtime: {runtime}")


def default_migration_path(source_path: Path) -> Path:
    name = source_path.name
    if name.endswith(".persona.json"):
        base_name = name[: -len(".persona.json")]
        target_name = base_name + ".v1.json"
        fallback_name = base_name + ".migrated.v1.json"
    elif name.endswith(".json"):
        base_name = name[:-5]
        target_name = base_name + ".v1.json"
        fallback_name = base_name + ".migrated.v1.json"
    else:
        base_name = name
        target_name = base_name + ".v1.json"
        fallback_name = base_name + ".migrated.v1.json"

    primary_path = source_path.with_name(target_name)
    if primary_path.exists() and primary_path.resolve() != source_path.resolve():
        return source_path.with_name(fallback_name)
    return primary_path
