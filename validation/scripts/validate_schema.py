#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = ROOT / "examples"
SCHEMA_PATH = ROOT / "schema" / "persona.schema.json"
VALID_DIR = ROOT / "validation" / "cases" / "valid"
INVALID_DIR = ROOT / "validation" / "cases" / "invalid"
RESULTS_PATH = ROOT / "validation" / "results" / "schema_results.json"


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


def sync_valid_cases() -> list[Path]:
    synced: list[Path] = []
    for source in example_paths():
        target = VALID_DIR / source.name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        synced.append(target)
    return synced


def invalid_case_specs(seed: dict[str, Any]) -> list[dict[str, Any]]:
    missing_required = copy.deepcopy(seed)
    missing_required.pop("description", None)

    wrong_type = copy.deepcopy(seed)
    wrong_type["traits"] = "patient, structured, clear"

    invalid_version = copy.deepcopy(seed)
    invalid_version["schema_version"] = "pop-1.0"

    unknown_field = copy.deepcopy(seed)
    unknown_field["operator_policy"] = {
        "approval_mode": "human-review",
        "safety_profile": "strict",
    }

    free_text_profile = {
        "schema_version": "pop-0.1",
        "id": "urn:pop:invalid:free-text-profile",
        "name": "Free Text Profile",
        "profile": (
            "You are a flexible mentor persona with broad emotional awareness, "
            "strong initiative, and no explicit structural boundary fields."
        ),
    }

    return [
        {
            "case_id": "missing_required_field",
            "filename": "missing_required_field.json",
            "payload": missing_required,
            "expected": "invalid",
            "notes": "Removed required field `description`.",
        },
        {
            "case_id": "wrong_field_type",
            "filename": "wrong_field_type.json",
            "payload": wrong_type,
            "expected": "invalid",
            "notes": "Changed `traits` from an array to a free-text string.",
        },
        {
            "case_id": "invalid_version",
            "filename": "invalid_version.json",
            "payload": invalid_version,
            "expected": "invalid",
            "notes": "Changed `schema_version` away from the allowed draft constant.",
        },
        {
            "case_id": "unknown_field",
            "filename": "unknown_field.json",
            "payload": unknown_field,
            "expected": "invalid",
            "notes": "Added an undeclared operational policy block.",
        },
        {
            "case_id": "free_text_profile",
            "filename": "free_text_profile.json",
            "payload": free_text_profile,
            "expected": "invalid",
            "notes": "Collapsed the persona into a vague free-text `profile` field.",
        },
    ]


def write_invalid_cases(cases: list[dict[str, Any]]) -> list[Path]:
    written: list[Path] = []
    for case in cases:
        target = INVALID_DIR / case["filename"]
        write_json(target, case["payload"])
        written.append(target)
    return written


def validate_payload(validator: Draft202012Validator, payload: Any) -> list[str]:
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    return [error.message for error in errors]


def build_case_result(
    *,
    case_id: str,
    category: str,
    source_path: Path,
    expected: str,
    base_notes: str,
    errors: list[str],
) -> dict[str, Any]:
    actual = "valid" if not errors else "invalid"
    return {
        "case_id": case_id,
        "category": category,
        "source": repo_rel(source_path),
        "expected": expected,
        "actual": actual,
        "pass_fail": "pass" if expected == actual else "fail",
        "notes": base_notes if not errors else f"{base_notes} First error: {errors[0]}",
        "errors": errors,
    }


def main() -> None:
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)

    valid_paths = sync_valid_cases()
    if not valid_paths:
        raise FileNotFoundError("No example personas were found in the examples/ directory.")

    seed_path = EXAMPLES_DIR / "mentor.persona.json"
    if not seed_path.exists():
        seed_path = example_paths()[0]
    seed = load_json(seed_path)

    invalid_cases = invalid_case_specs(seed)
    write_invalid_cases(invalid_cases)

    results: list[dict[str, Any]] = []
    for path in valid_paths:
        payload = load_json(path)
        results.append(
            build_case_result(
                case_id=path.stem,
                category="valid",
                source_path=path,
                expected="valid",
                base_notes="Repository example evaluated as a valid POP persona object.",
                errors=validate_payload(validator, payload),
            )
        )

    for case in invalid_cases:
        case_path = INVALID_DIR / case["filename"]
        payload = load_json(case_path)
        results.append(
            build_case_result(
                case_id=case["case_id"],
                category="invalid",
                source_path=case_path,
                expected=case["expected"],
                base_notes=case["notes"],
                errors=validate_payload(validator, payload),
            )
        )

    passed = sum(1 for result in results if result["pass_fail"] == "pass")
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_path": repo_rel(SCHEMA_PATH),
        "valid_case_count": sum(1 for result in results if result["category"] == "valid"),
        "invalid_case_count": sum(1 for result in results if result["category"] == "invalid"),
        "summary": {
            "total_cases": len(results),
            "passed": passed,
            "failed": len(results) - passed,
        },
        "cases": results,
    }
    write_json(RESULTS_PATH, payload)
    print(f"Wrote {repo_rel(RESULTS_PATH)}")


if __name__ == "__main__":
    main()
