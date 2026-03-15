from __future__ import annotations

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


def design_task(persona: Persona, context: TaskContext) -> str:
    context.update_progress(persona.name, "Designing")
    result = f"Designing with skills: {', '.join(persona.skills)}"
    context.set_result(persona.name, result)
    return result


def research_task(persona: Persona, context: TaskContext) -> str:
    design_result = context.get_result(design_persona.name)
    context.update_progress(persona.name, "Researching")
    result = f"Researching with skills: {', '.join(persona.skills)}"
    if design_result != "No result yet":
        result = f"{result} | informed by: {design_result}"
    context.set_result(persona.name, result)
    return result


def marketing_task(persona: Persona, context: TaskContext) -> str:
    research_result = context.get_result(research_persona.name)
    context.update_progress(persona.name, "Marketing")
    result = f"Marketing with skills: {', '.join(persona.skills)}"
    if research_result != "No result yet":
        result = f"{result} | built on: {research_result}"
    context.set_result(persona.name, result)
    return result


def workflow() -> None:
    print(f"Task: {task_context.task_name}")
    print("Starting Task:")

    print(design_task(design_persona, task_context))
    print(research_task(research_persona, task_context))
    print(marketing_task(marketing_persona, task_context))
    print()
    task_context.show_summary()


if __name__ == "__main__":
    workflow()
