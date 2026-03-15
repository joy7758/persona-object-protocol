from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from demos.task_context import TaskContext
from demos.task_registry import (
    build_deliverable,
    build_stage_output,
    resolve_persona_path,
    stage_handler_id_for,
    stage_sequence_for,
    supported_task_types,
)

DEFAULT_TASK_INPUT_PATH = PROJECT_ROOT / "demos" / "market_research_task.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "demos" / "generated"


def load_persona_loader_module() -> Any:
    # Load the lightweight demo loader directly to avoid package-level side effects.
    module_path = PROJECT_ROOT / "pop" / "persona_loader.py"
    spec = importlib.util.spec_from_file_location("persona_loader_demo", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load persona loader from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PERSONA_LOADER_MODULE = load_persona_loader_module()
Persona = PERSONA_LOADER_MODULE.Persona
load_persona = PERSONA_LOADER_MODULE.load_persona


def snapshot_result(result: dict[str, object]) -> dict[str, object]:
    return {
        "stage_name": result.get("stage_name"),
        "handler_id": result.get("handler_id"),
        "persona_name": result.get("persona_name"),
        "role": result.get("role"),
        "task_output": result.get("task_output"),
    }


def load_task_input(file_path: Path) -> dict[str, Any]:
    with file_path.open(encoding="utf-8") as file:
        return json.load(file)


def normalize_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized = [str(item).strip() for item in value if str(item).strip()]
    return normalized


def validate_task_input(task_input: dict[str, Any]) -> None:
    if not str(task_input.get("task_name", "")).strip():
        raise ValueError("Task input requires a non-empty `task_name`.")
    task_type = str(task_input.get("task_type", "")).strip()
    supported = supported_task_types()
    if task_type not in supported:
        supported_names = ", ".join(sorted(supported))
        raise ValueError(
            f"Unsupported `task_type`: {task_type or '(missing)'}. Expected one of: {supported_names}."
        )
    inputs = task_input.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("Task input requires an `inputs` object.")
    if not str(inputs.get("subject_name", "")).strip():
        raise ValueError("Task input requires `inputs.subject_name`.")
    if not str(inputs.get("subject_category", "")).strip():
        raise ValueError("Task input requires `inputs.subject_category`.")
    attributes = inputs.get("subject_attributes")
    if not isinstance(attributes, list):
        raise ValueError("Task input requires `inputs.subject_attributes` as a list.")
    if not any(str(item).strip() for item in attributes):
        raise ValueError("Task input requires at least one non-empty subject attribute.")
    objectives = task_input.get("objectives")
    if not isinstance(objectives, list) or not any(str(item).strip() for item in objectives):
        raise ValueError("Task input requires at least one objective.")


def normalize_task_input(raw_task_input: dict[str, Any]) -> dict[str, Any]:
    if "inputs" in raw_task_input and isinstance(raw_task_input["inputs"], dict):
        raw_inputs = raw_task_input["inputs"]
        normalized = {
            "task_name": str(raw_task_input.get("task_name") or "Untitled Persona Workflow"),
            "task_type": str(raw_task_input.get("task_type") or "market_research"),
            "inputs": {
                "subject_name": str(
                    raw_inputs.get("subject_name")
                    or raw_inputs.get("product_name")
                    or "Unknown subject"
                ),
                "subject_category": str(
                    raw_inputs.get("subject_category")
                    or raw_inputs.get("product_category")
                    or "General"
                ),
                "subject_attributes": normalize_text_list(
                    raw_inputs.get("subject_attributes") or raw_inputs.get("features")
                ),
                "target_audience": str(
                    raw_inputs.get("target_audience") or "General audience"
                ),
                "constraints": normalize_text_list(raw_inputs.get("constraints")),
                "success_metrics": normalize_text_list(raw_inputs.get("success_metrics")),
            },
            "objectives": normalize_text_list(raw_task_input.get("objectives")),
        }
    else:
        product = raw_task_input.get("product", {})
        normalized = {
            "task_name": str(raw_task_input.get("task_name") or "Untitled Persona Workflow"),
            "task_type": str(raw_task_input.get("task_type") or "market_research"),
            "inputs": {
                "subject_name": str(
                    (product.get("name") or "Unknown subject")
                    if isinstance(product, dict)
                    else "Unknown subject"
                ),
                "subject_category": str(
                    (product.get("category") or "General")
                    if isinstance(product, dict)
                    else "General"
                ),
                "subject_attributes": normalize_text_list(
                    product.get("features") if isinstance(product, dict) else []
                ),
                "target_audience": str(
                    raw_task_input.get("target_audience") or "General audience"
                ),
                "constraints": normalize_text_list(raw_task_input.get("constraints")),
                "success_metrics": normalize_text_list(raw_task_input.get("success_metrics")),
            },
            "objectives": normalize_text_list(raw_task_input.get("objectives")),
        }
    validate_task_input(normalized)
    return normalized


def load_personas_for_task(task_type: str) -> dict[str, Persona]:
    personas: dict[str, Persona] = {}
    for stage in stage_sequence_for(task_type):
        if stage.persona_id in personas:
            continue
        persona_path = resolve_persona_path(stage.persona_id, PROJECT_ROOT)
        personas[stage.persona_id] = load_persona(persona_path)
    return personas


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "deliverable"


def default_output_path(task_input: dict[str, Any]) -> Path:
    task_name = str(task_input.get("task_name") or "persona_workflow")
    return DEFAULT_OUTPUT_DIR / f"{slugify(task_name)}.deliverable.json"


def resolve_project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def write_deliverable(output_path: Path, payload: dict[str, Any]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def run_stage(
    task_type: str,
    stage_definition: Any,
    persona: Persona,
    context: TaskContext,
) -> dict[str, object]:
    previous_results: list[dict[str, object]] = []
    for dependency_stage in stage_definition.depends_on:
        previous_result = context.get_stage_result(dependency_stage)
        if previous_result:
            previous_results.append(snapshot_result(previous_result))

    context.update_progress(
        persona.name,
        stage_definition.progress_label,
        stage_definition.stage_name,
    )
    result = {
        "stage_name": stage_definition.stage_name,
        "handler_id": stage_handler_id_for(task_type, stage_definition.stage_name),
        "persona_id": stage_definition.persona_id,
        "persona_name": persona.name,
        "role": persona.role,
        "skills": persona.skills,
        "task_output": build_stage_output(
            task_type,
            stage_definition.stage_name,
            context.task_input,
        ),
        "previous_results": previous_results,
    }
    context.set_result(persona.name, result, stage_definition.stage_name)
    return result


def workflow(task_input_path: Path, output_path: Path | None = None) -> Path:
    raw_task_input = load_task_input(resolve_project_path(task_input_path))
    task_input = normalize_task_input(raw_task_input)
    task_context = TaskContext(
        str(task_input.get("task_name", "Untitled Persona Workflow")),
        str(task_input.get("task_type", "market_research")),
        task_input,
    )
    personas = load_personas_for_task(task_context.task_type)
    stage_sequence = stage_sequence_for(task_context.task_type)

    print(f"Task: {task_context.task_name}")
    print("Task Input:")
    print(json.dumps(task_input, indent=2))
    print()
    print("Starting Task:")

    for stage_definition in stage_sequence:
        persona = personas[stage_definition.persona_id]
        result = run_stage(
            task_context.task_type,
            stage_definition,
            persona,
            task_context,
        )
        print(json.dumps(result, indent=2))

    task_context.set_final_deliverable(
        build_deliverable(task_context.task_type, task_context)
    )

    print()
    task_context.show_summary()
    print()
    print("Final Deliverable:")
    deliverable = task_context.get_task_output()
    print(json.dumps(deliverable, indent=2))

    resolved_output_path = (
        resolve_project_path(output_path)
        if output_path is not None
        else default_output_path(task_input)
    )
    write_deliverable(resolved_output_path, deliverable)
    print()
    try:
        display_path = resolved_output_path.relative_to(PROJECT_ROOT)
    except ValueError:
        display_path = resolved_output_path
    print(f"Wrote deliverable: {display_path}")
    return resolved_output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the persona workflow demo with dynamic task input. "
            "External plugin packages can be added with plugin_config.json or "
            "POP_PLUGIN_CONFIG_FILE, and overridden with "
            "POP_PLUGIN_PACKAGES and POP_PLUGIN_PACKAGE_PATHS."
        )
    )
    parser.add_argument(
        "--task-input",
        type=Path,
        default=DEFAULT_TASK_INPUT_PATH,
        help="Path to the task input JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path for the generated deliverable JSON file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    workflow(args.task_input, args.output)
