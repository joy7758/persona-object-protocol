from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def detect_schema_kind(payload: dict[str, Any]) -> str:
    if payload.get("kind") == "persona-object":
        return "v1"
    if payload.get("schema_version") == "pop-0.1":
        return "pop-0.1"
    raise ValueError("Unable to detect POP object type. Expected `kind` or `schema_version`.")


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
        "issuer": "langchain-pop-legacy-migration",
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


def load_pop(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        payload = source
        source_label = None
    else:
        path = Path(source).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        payload = load_json(path)
        source_label = path.as_posix()

    schema_kind = detect_schema_kind(payload)
    if schema_kind == "v1":
        return payload
    return migrate_pop01_object(payload, source_label=source_label)


def _boundary_instruction(boundary_name: str, boundary_value: Any) -> str:
    if isinstance(boundary_value, bool):
        if boundary_value is False:
            return f"- `{boundary_name}`: do not claim authority in this area."
        return (
            f"- `{boundary_name}`: the persona object does not prohibit this area, "
            "but runtime policy still decides whether action is allowed."
        )

    decision = boundary_value["decision"]
    reason = boundary_value.get("reason", "")
    suffix = f" Reason: {reason}" if reason else ""

    if decision == "requires-review":
        return f"- `{boundary_name}`: require human or policy review before acting.{suffix}"
    if decision == "disallow":
        return f"- `{boundary_name}`: do not act as if authority is granted here.{suffix}"
    if decision == "out-of-scope":
        return f"- `{boundary_name}`: treat as outside the persona's scope.{suffix}"
    if decision == "allow":
        return (
            f"- `{boundary_name}`: this boundary is not restrictive by itself; "
            f"still rely on runtime policy.{suffix}"
        )
    return f"- `{boundary_name}`: boundary is unspecified; respond conservatively.{suffix}"


def build_langchain_system_prompt(
    source: str | Path | dict[str, Any],
    *,
    extra_instructions: str | None = None,
) -> str:
    pop_object = load_pop(source)
    boundary_lines = [
        _boundary_instruction(name, value) for name, value in pop_object["boundaries"].items()
    ]
    provenance = pop_object["provenance"]
    provenance_bits = []
    if "author" in provenance:
        provenance_bits.append(f"author={provenance['author']}")
    if "issuer" in provenance:
        provenance_bits.append(f"issuer={provenance['issuer']}")
    provenance_bits.append(f"created={provenance['created']}")

    lines = [
        "You are operating under a Persona Object Protocol (POP) persona object.",
        f"Role: {pop_object['role']}",
        f"Traits: {', '.join(pop_object['traits'])}",
        f"Object id: {pop_object['id']}",
        f"Version: {pop_object['version']}",
        f"Status: {pop_object['status']}",
        f"Provenance: {', '.join(provenance_bits)}",
        "Persona boundaries:",
        *boundary_lines,
        "Honor these persona boundaries during reasoning and tool use.",
        "Do not treat persona boundaries as permission grants.",
        "If runtime policy and persona boundaries conflict, follow the stricter constraint.",
    ]
    if extra_instructions:
        lines.extend(["Additional runtime instructions:", extra_instructions.strip()])
    return "\n".join(lines)
