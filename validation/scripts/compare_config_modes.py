#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = ROOT / "examples"
MONOLITHIC_DIR = ROOT / "validation" / "cases" / "monolithic"
SEPARATED_DIR = ROOT / "validation" / "cases" / "separated"
RESULTS_PATH = ROOT / "validation" / "results" / "comparison_results.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def repo_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def example_paths() -> list[Path]:
    persona_examples = sorted(EXAMPLES_DIR.glob("*.persona.json"))
    if persona_examples:
        return persona_examples
    return sorted(EXAMPLES_DIR.glob("*.json"))


def choose_canonical_persona() -> tuple[Path, dict[str, Any]]:
    preferred = EXAMPLES_DIR / "mentor.persona.json"
    source = preferred if preferred.exists() else example_paths()[0]
    return source, load_json(source)


def role_label(persona: dict[str, Any]) -> str:
    for anchor in persona.get("anchors", []):
        if anchor.get("type") == "role":
            return str(anchor.get("value", ""))
    return ""


def build_role_change_scenario(persona: dict[str, Any]) -> dict[str, Any]:
    current_role = role_label(persona)
    return {
        "from": {
            "id": persona["id"],
            "name": persona["name"],
            "description": persona["description"],
            "role_label": current_role,
        },
        "to": {
            "id": persona["id"].replace("structured-guidance", "strategic-guidance"),
            "name": persona["name"].replace("Structured", "Strategic"),
            "description": (
                "A mentor persona oriented toward strategic planning and steady skill development."
            ),
            "role_label": current_role.replace("skill-building", "strategic"),
        },
    }


def build_monolithic_config(persona: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    current = scenario["from"]
    return {
        "schema_version": persona["schema_version"],
        "role_id": current["id"],
        "display_name": current["name"],
        "persona_description": current["description"],
        "traits": persona["traits"],
        "anchors": copy.deepcopy(persona["anchors"]),
        "behavior": copy.deepcopy(persona["behavior"]),
        "memory_namespace": "persona/mentor/progress-log",
        "memory_hooks": copy.deepcopy(persona["memory_hooks"]),
        "tool_settings": {
            "planner_profile": "mentor-default",
            "enabled_plugins": [plugin["name"] for plugin in persona["plugins"]],
            "role_label": current["role_label"],
        },
        "role_instructions": {
            "system_prompt": (
                f"You are {current['name']}, a {current['role_label']}. "
                f"{current['description']}"
            ),
            "handoff_policy": "Escalate to a human for professional advice requests.",
        },
        "ui": {
            "badge": current["role_label"],
            "header": current["name"],
        },
    }


def build_separated_bundle(persona: dict[str, Any]) -> dict[str, Any]:
    persona_copy = copy.deepcopy(persona)
    runtime_context = {
        "persona_source": "validation/cases/separated/persona_object.json",
        "memory": {
            "hook_binding": "progress-log",
            "namespace": "persona/default-progress-log",
        },
        "tool_settings": {
            "enabled_plugins": [plugin["name"] for plugin in persona["plugins"]],
            "planner_profile": "default",
        },
        "role_instructions": {
            "system_prompt_template": (
                "Use the attached persona object as the authoritative source of role identity, tone, and boundaries."
            ),
            "handoff_policy": "Escalate to a human for professional advice requests.",
        },
        "ui": {
            "badge_source": "persona_object.name",
            "header_source": "persona_object.name",
        },
    }
    return {
        "persona_object": persona_copy,
        "runtime_context": runtime_context,
    }


def collect_string_paths(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    if isinstance(value, dict):
        items: list[tuple[str, str]] = []
        for key, nested in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else key
            items.extend(collect_string_paths(nested, next_prefix))
        return items
    if isinstance(value, list):
        items: list[tuple[str, str]] = []
        for index, nested in enumerate(value):
            next_prefix = f"{prefix}[{index}]"
            items.extend(collect_string_paths(nested, next_prefix))
        return items
    if isinstance(value, str):
        return [(prefix, value)]
    return []


def collect_change_paths(bundle: dict[str, Any], scenario: dict[str, Any]) -> list[str]:
    current = scenario["from"]
    exact_values = {
        current["id"],
        current["name"],
        current["description"],
        current["role_label"],
    }
    identity_tokens = {"mentor", "structured-guidance", "structured mentor", "skill-building mentor"}

    matched_paths = []
    for path, text in collect_string_paths(bundle):
        normalized = text.lower()
        if text in exact_values or any(token in normalized for token in identity_tokens):
            matched_paths.append(path)
    return sorted(set(matched_paths))


def build_mode_result(
    *,
    mode: str,
    artifact_paths: list[Path],
    bundle: dict[str, Any],
    scenario: dict[str, Any],
    canonical_paths: set[str],
    portability: str,
    boundary_clarity: str,
    auditability: str,
    drift_risk: str,
    notes: str,
) -> dict[str, Any]:
    change_paths = collect_change_paths(bundle, scenario)
    unrelated_paths = [path for path in change_paths if path not in canonical_paths]
    return {
        "mode": mode,
        "artifact_paths": [repo_rel(path) for path in artifact_paths],
        "update_role_identity_steps": len(change_paths),
        "affected_unrelated_fields": len(unrelated_paths),
        "change_paths": change_paths,
        "unrelated_change_paths": unrelated_paths,
        "portability": portability,
        "boundary_clarity": boundary_clarity,
        "role_change_auditability": auditability,
        "accidental_drift_risk": drift_risk,
        "notes": notes,
    }


def main() -> None:
    source_path, persona = choose_canonical_persona()
    scenario = build_role_change_scenario(persona)

    monolithic_config = build_monolithic_config(persona, scenario)
    monolithic_path = MONOLITHIC_DIR / "monolithic_config.json"
    write_json(monolithic_path, monolithic_config)

    separated_bundle = build_separated_bundle(persona)
    separated_persona_path = SEPARATED_DIR / "persona_object.json"
    separated_runtime_path = SEPARATED_DIR / "runtime_context.json"
    write_json(separated_persona_path, separated_bundle["persona_object"])
    write_json(separated_runtime_path, separated_bundle["runtime_context"])

    results = [
        build_mode_result(
            mode="monolithic",
            artifact_paths=[monolithic_path],
            bundle=monolithic_config,
            scenario=scenario,
            canonical_paths={
                "role_id",
                "display_name",
                "persona_description",
                "anchors[0].value",
            },
            portability="low",
            boundary_clarity="weak",
            auditability="low",
            drift_risk="higher",
            notes=(
                "Role identity is duplicated across prompt, memory, tool, and UI fields, "
                "so changes spill into operational configuration."
            ),
        ),
        build_mode_result(
            mode="separated",
            artifact_paths=[separated_persona_path, separated_runtime_path],
            bundle=separated_bundle,
            scenario=scenario,
            canonical_paths={
                "persona_object.id",
                "persona_object.name",
                "persona_object.description",
                "persona_object.anchors[0].value",
            },
            portability="high",
            boundary_clarity="strong",
            auditability="high",
            drift_risk="lower",
            notes=(
                "Role identity remains concentrated in the canonical POP object while runtime settings stay generic."
            ),
        ),
    ]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "canonical_source": repo_rel(source_path),
        "scenario": scenario,
        "modes": results,
    }
    write_json(RESULTS_PATH, payload)
    print(f"Wrote {repo_rel(RESULTS_PATH)}")


if __name__ == "__main__":
    main()
