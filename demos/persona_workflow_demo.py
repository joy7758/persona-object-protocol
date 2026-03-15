from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pop.persona_loader import load_persona


design_persona = load_persona(PROJECT_ROOT / "personas" / "design_persona.json")
research_persona = load_persona(PROJECT_ROOT / "personas" / "researcher_persona.json")
marketing_persona = load_persona(PROJECT_ROOT / "personas" / "marketing_persona.json")


def design_task(persona) -> str:
    return f"Designing with skills: {', '.join(persona.skills)}"


def research_task(persona) -> str:
    return f"Researching with skills: {', '.join(persona.skills)}"


def marketing_task(persona) -> str:
    return f"Marketing with skills: {', '.join(persona.skills)}"


def workflow() -> None:
    print(f"Design Task: {design_task(design_persona)}")
    print(f"Research Task: {research_task(research_persona)}")
    print(f"Marketing Task: {marketing_task(marketing_persona)}")


if __name__ == "__main__":
    workflow()
