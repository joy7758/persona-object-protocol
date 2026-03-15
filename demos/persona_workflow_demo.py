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
SUPPORTED_TASK_TYPES = {
    "market_research",
    "product_design",
    "ux_review",
}
TASK_TYPE_PROFILES: dict[str, dict[str, Any]] = {
    "market_research": {
        "design_default_objective": "Design a product concept",
        "research_default_objective": "Research market trends",
        "marketing_default_objective": "Create marketing strategy",
        "design_focus": [
            "clarify the value proposition",
            "connect concept choices to buyer expectations",
            "prepare a market-aware design brief",
        ],
        "research_focus": [
            "collect supporting market signals",
            "distill concise findings",
            "translate evidence into technical context",
        ],
        "marketing_focus": [
            "turn research into positioning",
            "shape a campaign-ready narrative",
            "package the final deliverable",
        ],
        "deliverable_type": "market_strategy_report",
    },
    "product_design": {
        "design_default_objective": "Shape the product concept",
        "research_default_objective": "Review design constraints and competitive cues",
        "marketing_default_objective": "Prepare launch messaging for the concept",
        "design_focus": [
            "define the concept direction",
            "prioritize user-facing differentiators",
            "keep the concept buildable under constraints",
        ],
        "research_focus": [
            "compare adjacent product patterns",
            "identify feasibility and usability constraints",
            "surface practical tradeoffs for the concept",
        ],
        "marketing_focus": [
            "translate the concept into launch language",
            "align story with buyer expectations",
            "package the concept as a reviewable brief",
        ],
        "deliverable_type": "product_concept_brief",
    },
    "ux_review": {
        "design_default_objective": "Define a better checkout experience",
        "research_default_objective": "Identify friction and usage patterns",
        "marketing_default_objective": "Package the UX improvement plan for rollout",
        "design_focus": [
            "map the intended user journey",
            "reduce points of hesitation",
            "prepare a concise improvement concept",
        ],
        "research_focus": [
            "identify friction signals",
            "connect issues to user behavior patterns",
            "prioritize what should change first",
        ],
        "marketing_focus": [
            "frame the UX work for stakeholders",
            "turn findings into an adoption story",
            "package a rollout-ready improvement plan",
        ],
        "deliverable_type": "ux_improvement_plan",
    },
}


def snapshot_result(result: dict[str, object]) -> dict[str, object]:
    return {
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
    if task_type not in SUPPORTED_TASK_TYPES:
        supported = ", ".join(sorted(SUPPORTED_TASK_TYPES))
        raise ValueError(
            f"Unsupported `task_type`: {task_type or '(missing)'}. Expected one of: {supported}."
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


def subject_inputs(task_input: dict[str, Any]) -> dict[str, Any]:
    return task_input.get("inputs", {})


def summarize_subject(task_input: dict[str, Any]) -> str:
    inputs = subject_inputs(task_input)
    feature_list = ", ".join(inputs.get("subject_attributes", [])) or "core attributes"
    return (
        f"{inputs.get('subject_name', 'Unknown subject')} in "
        f"{inputs.get('subject_category', 'Unknown')}"
        f" with {feature_list}"
    )


def with_indefinite_article(text: str) -> str:
    article = "an" if text[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {text}"


def infer_market_trends(task_input: dict[str, Any]) -> list[str]:
    inputs = subject_inputs(task_input)
    features = {str(feature).lower() for feature in inputs.get("subject_attributes", [])}
    trends: list[str] = []
    if "5g" in features:
        trends.append("5G adoption remains a purchase driver in premium devices")
    if "fast charging" in features:
        trends.append("Battery convenience influences upgrade decisions")
    if "touchscreen" in features:
        trends.append("Large responsive displays remain central to daily usage")
    if str(inputs.get("subject_category", "")).lower() == "electronics":
        trends.append("Consumers compare feature density with price sensitivity")
    return trends or ["General market demand should be validated with recent signals"]


def infer_design_constraints(task_input: dict[str, Any]) -> list[str]:
    inputs = subject_inputs(task_input)
    constraints = inputs.get("constraints", [])
    if constraints:
        return constraints
    return [
        "Balance concept ambition with implementation feasibility",
        "Keep differentiation obvious to the target audience",
    ]


def infer_ux_findings(task_input: dict[str, Any]) -> list[str]:
    inputs = subject_inputs(task_input)
    attributes = {str(item).lower() for item in inputs.get("subject_attributes", [])}
    findings: list[str] = []
    if "form abandonment" in attributes:
        findings.append("Long form steps likely interrupt momentum before payment.")
    if "payment trust" in attributes:
        findings.append("Trust cues near payment decisions need to be more visible.")
    if "mobile checkout" in attributes:
        findings.append("Mobile users need fewer taps and clearer progress markers.")
    return findings or [
        "Review friction around the primary user path and prioritize the highest drop-off points."
    ]


def objective_for(
    task_input: dict[str, Any],
    index: int,
    default: str,
) -> str:
    objectives = task_input.get("objectives", [])
    if index < len(objectives):
        return str(objectives[index])
    return default


def profile_for(task_type: str) -> dict[str, Any]:
    return TASK_TYPE_PROFILES[task_type]


def build_design_output(task_input: dict[str, Any]) -> dict[str, Any]:
    task_type = str(task_input.get("task_type"))
    inputs = subject_inputs(task_input)
    profile = profile_for(task_type)
    if task_type == "market_research":
        return {
            "summary": f"Design a concept for {summarize_subject(task_input)}",
            "objective": objective_for(
                task_input, 0, str(profile["design_default_objective"])
            ),
            "subject": inputs,
            "focus": profile["design_focus"],
        }
    if task_type == "product_design":
        return {
            "summary": (
                f"Shape the product direction for {inputs['subject_name']} with "
                f"attention to concept clarity and buildability"
            ),
            "objective": objective_for(
                task_input, 0, str(profile["design_default_objective"])
            ),
            "concept_direction": {
                "subject": inputs["subject_name"],
                "category": inputs["subject_category"],
                "hero_attributes": inputs["subject_attributes"][:3],
            },
            "focus": profile["design_focus"],
        }
    return {
        "summary": (
            f"Define an improved experience for {inputs['subject_name']} in "
            f"{inputs['subject_category']}"
        ),
        "objective": objective_for(
            task_input, 0, str(profile["design_default_objective"])
        ),
        "experience_map": {
            "subject": inputs["subject_name"],
            "primary_friction_signals": inputs["subject_attributes"][:3],
            "target_audience": inputs.get("target_audience"),
        },
        "focus": profile["design_focus"],
    }


def build_research_output(task_input: dict[str, Any]) -> dict[str, Any]:
    task_type = str(task_input.get("task_type"))
    inputs = subject_inputs(task_input)
    profile = profile_for(task_type)
    if task_type == "market_research":
        return {
            "summary": f"Research market demand for {inputs['subject_name']}",
            "objective": objective_for(
                task_input, 1, str(profile["research_default_objective"])
            ),
            "market_trends": infer_market_trends(task_input),
            "focus": profile["research_focus"],
        }
    if task_type == "product_design":
        return {
            "summary": (
                f"Research constraints and adjacent patterns for {inputs['subject_name']}"
            ),
            "objective": objective_for(
                task_input, 1, str(profile["research_default_objective"])
            ),
            "design_constraints": infer_design_constraints(task_input),
            "focus": profile["research_focus"],
        }
    return {
        "summary": f"Research UX friction patterns for {inputs['subject_name']}",
        "objective": objective_for(
            task_input, 1, str(profile["research_default_objective"])
        ),
        "ux_findings": infer_ux_findings(task_input),
        "focus": profile["research_focus"],
    }


def build_marketing_output(task_input: dict[str, Any]) -> dict[str, Any]:
    task_type = str(task_input.get("task_type"))
    inputs = subject_inputs(task_input)
    profile = profile_for(task_type)
    attributes = ", ".join(inputs["subject_attributes"])
    if task_type == "market_research":
        return {
            "summary": f"Create marketing strategy for {inputs['subject_name']}",
            "objective": objective_for(
                task_input, 2, str(profile["marketing_default_objective"])
            ),
            "positioning": (
                f"{inputs['subject_name']} is positioned as "
                f"{with_indefinite_article(inputs['subject_category'].lower())} offer that "
                f"combines {attributes} into one concise value story."
            ),
            "campaign_hooks": [
                f"Lead with {inputs['subject_attributes'][0] if inputs['subject_attributes'] else 'the clearest differentiator'} as the hero differentiator",
                "Use research-backed proof points in launch messaging",
                "Connect product utility to everyday buyer outcomes",
            ],
            "focus": profile["marketing_focus"],
        }
    if task_type == "product_design":
        return {
            "summary": f"Prepare launch framing for the {inputs['subject_name']} concept",
            "objective": objective_for(
                task_input, 2, str(profile["marketing_default_objective"])
            ),
            "launch_story": (
                f"Present {inputs['subject_name']} as a concept that turns {attributes} "
                "into a coherent premium product direction."
            ),
            "stakeholder_hooks": [
                "Frame the concept as feasible, differentiated, and buyer-relevant",
                "Use constraints to explain why the chosen direction is disciplined",
            ],
            "focus": profile["marketing_focus"],
        }
    return {
        "summary": f"Package the UX rollout plan for {inputs['subject_name']}",
        "objective": objective_for(
            task_input, 2, str(profile["marketing_default_objective"])
        ),
        "rollout_story": (
            f"Position the {inputs['subject_name']} update as a friction-reduction effort "
            "that improves confidence and completion rates."
        ),
        "stakeholder_hooks": [
            "Tie each improvement to a visible user pain point",
            "Explain the rollout in terms of reduced friction and clearer trust cues",
        ],
        "focus": profile["marketing_focus"],
    }


def write_deliverable(output_path: Path, payload: dict[str, Any]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def design_task(persona: Persona, context: TaskContext) -> dict[str, object]:
    context.update_progress(persona.name, "Designing")
    result = {
        "persona_name": persona.name,
        "role": persona.role,
        "skills": persona.skills,
        "task_output": build_design_output(context.task_input),
        "previous_results": [],
    }
    context.set_result(persona.name, result)
    return result


def research_task(
    persona: Persona,
    context: TaskContext,
    design_persona_name: str,
) -> dict[str, object]:
    design_result = context.get_result(design_persona_name)
    context.update_progress(persona.name, "Researching")
    result = {
        "persona_name": persona.name,
        "role": persona.role,
        "skills": persona.skills,
        "task_output": build_research_output(context.task_input),
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
    profile = profile_for(context.task_type)
    inputs = subject_inputs(context.task_input)
    design_result = context.get_result(design_persona_name)
    research_result = context.get_result(research_persona_name)
    context.update_progress(persona.name, "Marketing")
    result = {
        "persona_name": persona.name,
        "role": persona.role,
        "skills": persona.skills,
        "task_output": build_marketing_output(context.task_input),
        "previous_results": [
            snapshot_result(item) for item in [design_result, research_result] if item
        ],
    }
    context.set_result(persona.name, result)
    context.set_final_deliverable(
        {
            "task_name": context.task_name,
            "task_type": context.task_type,
            "deliverable_type": profile["deliverable_type"],
            "inputs": inputs,
            "objectives": context.task_input.get("objectives", []),
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
    raw_task_input = load_task_input(resolve_project_path(task_input_path))
    task_input = normalize_task_input(raw_task_input)
    task_context = TaskContext(
        str(task_input.get("task_name", "Untitled Persona Workflow")),
        str(task_input.get("task_type", "market_research")),
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
