from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pop import load_persona


TASK_BRIEF = "Plan the first POP landing page and launch outline"
PERSONAS = {
    "designer": ROOT / "examples" / "pop_team_demo" / "personas" / "designer.json",
    "engineer": ROOT / "examples" / "pop_team_demo" / "personas" / "engineer.json",
    "marketing_manager": ROOT / "examples" / "pop_team_demo" / "personas" / "marketing_manager.json",
}


def create_agent(path: Path, verbose: bool = True):
    from crewai import Agent

    persona = load_persona(path)
    return Agent(
        role=persona.summary,
        goal="; ".join(persona.task_orientation),
        backstory=" ".join([*persona.traits, *persona.communication_style]),
        verbose=verbose,
    )


def build_live_crew():
    from crewai import Crew, Task

    designer = create_agent(PERSONAS["designer"])
    engineer = create_agent(PERSONAS["engineer"])
    marketer = create_agent(PERSONAS["marketing_manager"])

    tasks = [
        Task(
            description=f"{TASK_BRIEF}. Focus on structure, onboarding, and interaction priorities.",
            expected_output="A concise landing-page UX direction.",
            agent=designer,
        ),
        Task(
            description=f"{TASK_BRIEF}. Focus on implementation feasibility, sections, and delivery constraints.",
            expected_output="A concise implementation-oriented recommendation.",
            agent=engineer,
        ),
        Task(
            description=f"{TASK_BRIEF}. Focus on positioning, messaging, and launch framing.",
            expected_output="A concise launch and messaging recommendation.",
            agent=marketer,
        ),
    ]

    return Crew(agents=[designer, engineer, marketer], tasks=tasks, verbose=True)


def main() -> int:
    try:
        from crewai import Agent, Task, Crew  # noqa: F401
    except Exception:
        print("CREWAI_NOT_INSTALLED")
        print("Install with: pip install crewai")
        return 0

    if not any(os.getenv(key) for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY")):
        print("MODEL_KEY_MISSING")
        print("Set a provider API key, for example OPENAI_API_KEY, before running the live demo.")
        return 0

    result = build_live_crew().kickoff()
    print("\n=== LIVE DEMO RESULT ===")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
