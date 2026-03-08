#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = ROOT / "examples"
PROJECTION_DIR = ROOT / "validation" / "cases" / "projection"
RESULTS_PATH = ROOT / "validation" / "results" / "projection_results.json"


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
    persona = load_json(source)
    write_json(PROJECTION_DIR / "canonical.persona.json", persona)
    return source, persona


def find_anchor_value(persona: dict[str, Any], anchor_type: str) -> str:
    for anchor in persona.get("anchors", []):
        if anchor.get("type") == anchor_type:
            return str(anchor.get("value", ""))
    return ""


def persona_field_buckets(persona: dict[str, Any]) -> dict[str, Any]:
    return {
        "identifier": persona["id"],
        "version": persona["schema_version"],
        "role_label": find_anchor_value(persona, "role"),
        "expressive_values": [
            persona["description"],
            persona["behavior"]["tone"],
            *persona["traits"],
            *persona["behavior"]["interaction_style"],
        ],
        "boundary_values": [
            *[anchor["value"] for anchor in persona["anchors"] if anchor["type"] == "boundary"],
            *persona["behavior"]["boundaries"],
        ],
        "governance_values": [
            persona["schema_version"],
            *[hook["id"] for hook in persona["memory_hooks"]],
            *[plugin["name"] for plugin in persona["plugins"]],
        ],
    }


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        items: list[str] = []
        for nested in value.values():
            items.extend(flatten_strings(nested))
        return items
    if isinstance(value, list):
        items: list[str] = []
        for nested in value:
            items.extend(flatten_strings(nested))
        return items
    if isinstance(value, str):
        return [value]
    return []


def contains_value(strings: list[str], target: str) -> bool:
    return any(target == item or target in item for item in strings)


def classify_bucket(
    *,
    values: list[str],
    flattened_strings: list[str],
    structured: bool,
) -> str:
    matched = sum(1 for value in values if contains_value(flattened_strings, value))
    if matched == len(values) and structured:
        return "complete"
    if matched > 0:
        return "weakened"
    return "lost"


def classify_governance(
    *,
    values: list[str],
    flattened_strings: list[str],
    structured: bool,
) -> str:
    matched = sum(1 for value in values if contains_value(flattened_strings, value))
    return "complete" if matched == len(values) and structured else "lost"


def prompt_based_projection(persona: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bool], str]:
    role_label = find_anchor_value(persona, "role")
    boundary_text = "; ".join(
        [anchor["value"] for anchor in persona["anchors"] if anchor["type"] == "boundary"]
        + persona["behavior"]["boundaries"]
    )
    prompt = (
        f"You are {persona['name']}, a {role_label}. "
        f"{persona['description']} "
        f"Traits: {', '.join(persona['traits'])}. "
        f"Tone: {persona['behavior']['tone']}. "
        f"Interaction style: {', '.join(persona['behavior']['interaction_style'])}. "
        f"Boundaries: {boundary_text}."
    )
    artifact = {
        "projection_type": "prompt_based",
        "system_prompt": prompt,
    }
    layout = {
        "structured_expressive": False,
        "structured_boundaries": False,
        "structured_governance": False,
    }
    note = "Flattened into a single prompt string with no stable slot for identity or governance metadata."
    return artifact, layout, note


def app_layer_role_model_projection(persona: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bool], str]:
    role_label = find_anchor_value(persona, "role")
    artifact = {
        "projection_type": "app_layer_role_model",
        "role_model": {
            "role_id": persona["id"],
            "persona_version": persona["schema_version"],
            "label": role_label,
            "summary": persona["description"],
            "style_profile": {
                "traits": persona["traits"],
                "tone": persona["behavior"]["tone"],
                "interaction_style": persona["behavior"]["interaction_style"],
            },
            "guardrails": {
                "boundary_statements": [
                    anchor["value"] for anchor in persona["anchors"] if anchor["type"] == "boundary"
                ]
                + persona["behavior"]["boundaries"]
            },
            "integration_hints": {
                "memory_hook_ids": [hook["id"] for hook in persona["memory_hooks"]],
                "plugin_names": [plugin["name"] for plugin in persona["plugins"]],
            },
        },
    }
    layout = {
        "structured_expressive": True,
        "structured_boundaries": True,
        "structured_governance": True,
    }
    note = "Mapped into explicit app-layer slots that preserve identity, style, boundaries, and integration hints."
    return artifact, layout, note


def agent_runtime_projection(persona: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bool], str]:
    role_label = find_anchor_value(persona, "role")
    artifact = {
        "projection_type": "agent_runtime",
        "runtime_contract": {
            "persona_ref": {
                "id": persona["id"],
                "schema_version": persona["schema_version"],
            },
            "identity": {
                "name": persona["name"],
                "role_label": role_label,
            },
            "behavior_contract": {
                "description": persona["description"],
                "traits": persona["traits"],
                "tone": persona["behavior"]["tone"],
                "interaction_style": persona["behavior"]["interaction_style"],
            },
            "boundary_contract": {
                "anchor_boundaries": [
                    anchor["value"] for anchor in persona["anchors"] if anchor["type"] == "boundary"
                ],
                "interaction_boundaries": persona["behavior"]["boundaries"],
            },
            "integration_contract": {
                "memory_hooks": persona["memory_hooks"],
                "plugins": persona["plugins"],
            },
        },
    }
    layout = {
        "structured_expressive": True,
        "structured_boundaries": True,
        "structured_governance": True,
    }
    note = "Retained as a runtime contract with separate identity, behavior, boundary, and integration sections."
    return artifact, layout, note


def evaluate_projection(
    projection_name: str,
    artifact_path: Path,
    artifact: dict[str, Any],
    layout: dict[str, bool],
    persona_fields: dict[str, Any],
    note: str,
) -> dict[str, Any]:
    flattened_strings = flatten_strings(artifact)
    result = {
        "projection": projection_name,
        "artifact_path": repo_rel(artifact_path),
        "identifier_preserved": "yes" if contains_value(flattened_strings, persona_fields["identifier"]) else "no",
        "version_preserved": "yes" if contains_value(flattened_strings, persona_fields["version"]) else "no",
        "role_label_preserved": "yes" if contains_value(flattened_strings, persona_fields["role_label"]) else "no",
        "expressive_tendencies": classify_bucket(
            values=persona_fields["expressive_values"],
            flattened_strings=flattened_strings,
            structured=layout["structured_expressive"],
        ),
        "interaction_boundaries": classify_bucket(
            values=persona_fields["boundary_values"],
            flattened_strings=flattened_strings,
            structured=layout["structured_boundaries"],
        ),
        "governance_status_metadata": classify_governance(
            values=persona_fields["governance_values"],
            flattened_strings=flattened_strings,
            structured=layout["structured_governance"],
        ),
        "notes": note,
    }
    return result


def main() -> None:
    source_path, persona = choose_canonical_persona()
    persona_fields = persona_field_buckets(persona)

    builders = [
        ("prompt_based", prompt_based_projection),
        ("app_layer_role_model", app_layer_role_model_projection),
        ("agent_runtime", agent_runtime_projection),
    ]

    projections: list[dict[str, Any]] = []
    for name, builder in builders:
        artifact, layout, note = builder(persona)
        artifact_path = PROJECTION_DIR / f"{name}.json"
        write_json(artifact_path, artifact)
        projections.append(
            evaluate_projection(
                projection_name=name,
                artifact_path=artifact_path,
                artifact=artifact,
                layout=layout,
                persona_fields=persona_fields,
                note=note,
            )
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "canonical_source": repo_rel(source_path),
        "canonical_persona_id": persona["id"],
        "canonical_persona_name": persona["name"],
        "projections": projections,
    }
    write_json(RESULTS_PATH, payload)
    print(f"Wrote {repo_rel(RESULTS_PATH)}")


if __name__ == "__main__":
    main()
