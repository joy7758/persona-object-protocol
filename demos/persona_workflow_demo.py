from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from demos.task_context import TaskContext
from pop.persona_loader import Persona, load_persona

DEFAULT_TASK_INPUT_PATH = PROJECT_ROOT / "demos" / "market_research_task.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "demos" / "generated"


def snapshot_result(result: dict[str, object]) -> dict[str, object]:
    return {
        "persona_name": result.get("persona_name"),
        "role": result.get("role"),
        "task_output": result.get("task_output"),
    }


def load_task_input(file_path: Path) -> dict[str, Any]:
    with file_path.open(encoding="utf-8") as file:
        return json.load(file)


def load_personas() -> tuple[Persona, Persona, Persona]:
    design_persona = load_persona(PROJECT_ROOT / "personas" / "design_persona.json")
    research_persona = load_persona(
        PROJECT_ROOT / "personas" / "researcher_persona.json"
    )
    marketing_persona = load_persona(
        PROJECT_ROOT / "personas" / "marketing_persona.json"
    )
    return design_persona, research_persona, marketing_persona


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "deliverable"


def default_output_path(task_input: dict[str, Any]) -> Path:
    task_name = str(task_input.get("task_name") or "persona_workflow")
    return DEFAULT_OUTPUT_DIR / f"{slugify(task_name)}.deliverable.json"


def resolve_project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def summarize_product(product: dict[str, Any]) -> str:
    feature_list = ", ".join(product.get("features", [])) or "core features"
    return (
        f"{product.get('name', 'Unknown product')} in {product.get('category', 'Unknown')}"
        f" with {feature_list}"
    )


def with_indefinite_article(text: str) -> str:
    article = "an" if text[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {text}"


def infer_market_trends(product: dict[str, Any]) -> list[str]:
    features = {str(feature).lower() for feature in product.get("features", [])}
    trends: list[str] = []
    if "5g" in features:
        trends.append("5G adoption remains a purchase driver in premium devices")
    if "fast charging" in features:
        trends.append("Battery convenience influences upgrade decisions")
    if "touchscreen" in features:
        trends.append("Large responsive displays remain central to daily usage")
    if str(product.get("category", "")).lower() == "electronics":
        trends.append("Consumers compare feature density with price sensitivity")
    return trends or ["General market demand should be validated with recent signals"]


def write_deliverable(output_path: Path, payload: dict[str, Any]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def design_task(persona: Persona, context: TaskContext) -> dict[str, object]:
    product = context.task_input.get("product", {})
    objectives = context.task_input.get("objectives", [])
    context.update_progress(persona.name, "Designing")
    result = {
        "persona_name": persona.name,
        "role": persona.role,
        "skills": persona.skills,
        "task_output": {
            "summary": (
                f"Design a concept for {summarize_product(product)} using "
                f"{', '.join(persona.skills)}"
            ),
            "objective": objectives[0] if objectives else "Design a product concept",
            "product": product,
            "focus": [
                "clarify the user journey",
                "reduce interface friction",
                "prepare a usable design brief",
            ],
        },
        "previous_results": [],
    }
    context.set_result(persona.name, result)
    return result


def research_task(
    persona: Persona,
    context: TaskContext,
    design_persona_name: str,
) -> dict[str, object]:
    product = context.task_input.get("product", {})
    objectives = context.task_input.get("objectives", [])
    design_result = context.get_result(design_persona_name)
    context.update_progress(persona.name, "Researching")
    result = {
        "persona_name": persona.name,
        "role": persona.role,
        "skills": persona.skills,
        "task_output": {
            "summary": (
                f"Research market demand for {product.get('name', 'the product')} using "
                f"{', '.join(persona.skills)}"
            ),
            "objective": (
                objectives[1] if len(objectives) > 1 else "Research market trends"
            ),
            "market_trends": infer_market_trends(product),
            "focus": [
                "collect supporting market signals",
                "distill concise findings",
                "translate evidence into technical context",
            ],
        },
        "previous_results": [snapshot_result(design_result)] if design_result else [],
    }
    context.set_result(persona.name, result)
    return result


def marketing_task(
    persona: Persona,
    context: TaskContext,
    design_persona_name: str,
    research_persona_name: str,
) -> dict[str, object]:
    product = context.task_input.get("product", {})
    objectives = context.task_input.get("objectives", [])
    design_result = context.get_result(design_persona_name)
    research_result = context.get_result(research_persona_name)
    context.update_progress(persona.name, "Marketing")
    result = {
        "persona_name": persona.name,
        "role": persona.role,
        "skills": persona.skills,
        "task_output": {
            "summary": (
                f"Create marketing strategy for {product.get('name', 'the product')} "
                f"with {', '.join(persona.skills)}"
            ),
            "objective": (
                objectives[2] if len(objectives) > 2 else "Create marketing strategy"
            ),
            "positioning": (
                f"{product.get('name', 'The product')} is positioned as "
                f"{with_indefinite_article(str(product.get('category', 'product')).lower())} "
                f"offer that combines "
                f"{', '.join(product.get('features', []))} into one concise value story."
            ),
            "campaign_hooks": [
                f"Lead with {product.get('features', ['key features'])[0]} as the hero feature",
                "Use research-backed proof points in launch messaging",
                "Connect product utility to everyday buyer outcomes",
            ],
            "focus": [
                "turn research into positioning",
                "shape a campaign-ready narrative",
                "package the final deliverable",
            ],
        },
        "previous_results": [
            snapshot_result(item) for item in [design_result, research_result] if item
        ],
    }
    context.set_result(persona.name, result)
    context.set_final_deliverable(
        {
            "task_name": context.task_name,
            "product": product,
            "objectives": objectives,
            "prepared_by": persona.name,
            "persona_sequence": [
                design_persona_name,
                research_persona_name,
                persona.name,
            ],
            "design_brief": design_result.get("task_output", {}),
            "research_summary": research_result.get("task_output", {}),
            "marketing_plan": result["task_output"],
        }
    )
    return result


def workflow(task_input_path: Path, output_path: Path | None = None) -> Path:
    task_input = load_task_input(resolve_project_path(task_input_path))
    task_context = TaskContext(
        str(task_input.get("task_name", "Untitled Persona Workflow")),
        task_input,
    )
    (
        design_persona,
        research_persona,
        marketing_persona,
    ) = load_personas()

    print(f"Task: {task_context.task_name}")
    print("Task Input:")
    print(json.dumps(task_input, indent=2))
    print()
    print("Starting Task:")

    print(json.dumps(design_task(design_persona, task_context), indent=2))
    print(
        json.dumps(
            research_task(research_persona, task_context, design_persona.name),
            indent=2,
        )
    )
    print(
        json.dumps(
            marketing_task(
                marketing_persona,
                task_context,
                design_persona.name,
                research_persona.name,
            ),
            indent=2,
        )
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
        description="Run the persona workflow demo with dynamic task input."
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
