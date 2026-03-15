from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from demos.task_context import TaskContext
from pop.persona_loader import Persona, load_persona


design_persona = load_persona(PROJECT_ROOT / "personas" / "design_persona.json")
research_persona = load_persona(PROJECT_ROOT / "personas" / "researcher_persona.json")
marketing_persona = load_persona(PROJECT_ROOT / "personas" / "marketing_persona.json")
task_context = TaskContext("Market Research & Design Collaboration")


def snapshot_result(result: dict[str, object]) -> dict[str, object]:
    return {
        "persona_name": result.get("persona_name"),
        "role": result.get("role"),
        "task_output": result.get("task_output"),
    }


def design_task(persona: Persona, context: TaskContext) -> dict[str, object]:
    context.update_progress(persona.name, "Designing")
    result = {
        "persona_name": persona.name,
        "role": persona.role,
        "skills": persona.skills,
        "task_output": {
            "summary": f"Designing with skills: {', '.join(persona.skills)}",
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


def research_task(persona: Persona, context: TaskContext) -> dict[str, object]:
    design_result = context.get_result(design_persona.name)
    context.update_progress(persona.name, "Researching")
    result = {
        "persona_name": persona.name,
        "role": persona.role,
        "skills": persona.skills,
        "task_output": {
            "summary": f"Researching with skills: {', '.join(persona.skills)}",
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


def marketing_task(persona: Persona, context: TaskContext) -> dict[str, object]:
    design_result = context.get_result(design_persona.name)
    research_result = context.get_result(research_persona.name)
    context.update_progress(persona.name, "Marketing")
    result = {
        "persona_name": persona.name,
        "role": persona.role,
        "skills": persona.skills,
        "task_output": {
            "summary": f"Marketing with skills: {', '.join(persona.skills)}",
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
            "prepared_by": persona.name,
            "persona_sequence": [
                design_persona.name,
                research_persona.name,
                marketing_persona.name,
            ],
            "design_brief": design_result.get("task_output", {}),
            "research_summary": research_result.get("task_output", {}),
            "marketing_plan": result["task_output"],
        }
    )
    return result


def workflow() -> None:
    print(f"Task: {task_context.task_name}")
    print("Starting Task:")

    print(json.dumps(design_task(design_persona, task_context), indent=2))
    print(json.dumps(research_task(research_persona, task_context), indent=2))
    print(json.dumps(marketing_task(marketing_persona, task_context), indent=2))
    print()
    task_context.show_summary()
    print()
    print("Final Deliverable:")
    print(json.dumps(task_context.get_task_output(), indent=2))


if __name__ == "__main__":
    workflow()
