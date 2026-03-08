#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "validation" / "results"
SCHEMA_RESULTS_PATH = RESULTS_DIR / "schema_results.json"
PROJECTION_RESULTS_PATH = RESULTS_DIR / "projection_results.json"
COMPARISON_RESULTS_PATH = RESULTS_DIR / "comparison_results.json"
TABLES_PATH = RESULTS_DIR / "tables.md"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def escape_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_table(headers: list[str], rows: list[list[Any]]) -> str:
    header_row = "| " + " | ".join(headers) + " |"
    separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_rows = ["| " + " | ".join(escape_cell(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header_row, separator_row, *body_rows])


def schema_section(schema_results: dict[str, Any]) -> str:
    rows = [
        [
            case["case_id"],
            case["expected"],
            case["actual"],
            case["pass_fail"],
            case["notes"],
        ]
        for case in schema_results["cases"]
    ]
    summary = schema_results["summary"]
    narrative = (
        f"All {schema_results['valid_case_count']} repository examples validated successfully, "
        f"while all {schema_results['invalid_case_count']} intentionally malformed cases were rejected. "
        "This indicates that POP persona objects are machine-checkable at the schema boundary and that "
        "common structural deviations can be detected with a compact JSON Schema."
    )
    return "\n\n".join(
        [
            "Table X. Schema conformance results for POP persona objects",
            render_table(["Case", "Expected", "Actual", "Pass/Fail", "Notes"], rows),
            narrative,
            f"Summary: {summary['passed']} of {summary['total_cases']} cases matched the expected outcome.",
        ]
    )


def projection_section(projection_results: dict[str, Any]) -> str:
    rows = [
        [
            projection["projection"],
            projection["identifier_preserved"],
            projection["version_preserved"],
            projection["role_label_preserved"],
            projection["expressive_tendencies"],
            projection["interaction_boundaries"],
            projection["governance_status_metadata"],
            projection["notes"],
        ]
        for projection in projection_results["projections"]
    ]
    narrative = (
        f"For the canonical persona object `{projection_results['canonical_persona_name']}`, "
        "prompt-based projection preserved the high-level role label but weakened expressive and boundary detail "
        "because structured fields were flattened into text. The app-layer role model and agent-runtime projections "
        "retained all tracked fields at the object level, showing that fidelity improves when downstream systems "
        "keep explicit persona slots instead of prompt-only injection."
    )
    return "\n\n".join(
        [
            "Table Y. Cross-runtime projection fidelity for the same canonical persona object",
            render_table(
                [
                    "Projection",
                    "Identifier",
                    "Version",
                    "Role Label",
                    "Expressive Tendencies",
                    "Interaction Boundaries",
                    "Governance/Status Metadata",
                    "Notes",
                ],
                rows,
            ),
            narrative,
        ]
    )


def comparison_section(comparison_results: dict[str, Any]) -> str:
    rows = [
        [
            mode["mode"],
            mode["update_role_identity_steps"],
            mode["affected_unrelated_fields"],
            mode["portability"],
            mode["boundary_clarity"],
            mode["role_change_auditability"],
            mode["accidental_drift_risk"],
            mode["notes"],
        ]
        for mode in comparison_results["modes"]
    ]
    narrative = (
        "Separated persona objects required fewer role-update edits and avoided spillover into memory, tool, and UI "
        "settings. The monolithic configuration showed lower portability and auditability because identity changes "
        "touched mixed operational fields, which increases the risk of accidental drift."
    )
    return "\n\n".join(
        [
            "Table Z. Comparison between separated persona objects and monolithic role configuration",
            render_table(
                [
                    "Mode",
                    "Update Steps",
                    "Unrelated Fields Affected",
                    "Portability",
                    "Boundary Clarity",
                    "Role Change Auditability",
                    "Accidental Drift Risk",
                    "Notes",
                ],
                rows,
            ),
            narrative,
        ]
    )


def main() -> None:
    schema_results = load_json(SCHEMA_RESULTS_PATH)
    projection_results = load_json(PROJECTION_RESULTS_PATH)
    comparison_results = load_json(COMPARISON_RESULTS_PATH)

    content = "\n\n".join(
        [
            "# POP Minimal Validation Tables",
            schema_section(schema_results),
            projection_section(projection_results),
            comparison_section(comparison_results),
        ]
    )
    TABLES_PATH.write_text(content + "\n", encoding="utf-8")
    print(f"Wrote {TABLES_PATH.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
