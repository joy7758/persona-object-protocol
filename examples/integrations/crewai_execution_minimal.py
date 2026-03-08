from __future__ import annotations

import json
from pathlib import Path

from pop import load_persona
from pop.integrations.crewai import (
    create_crewai_agent_kwargs,
    create_crewai_execution_scaffold,
)


ROOT = Path(__file__).resolve().parents[2]
PERSONA_PATH = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


def main() -> None:
    persona = load_persona(PERSONA_PATH)
    print("CrewAI Agent Kwargs")
    print(
        json.dumps(
            create_crewai_agent_kwargs(
                persona,
                tools=["case_lookup"],
                llm="mock-llm",
                verbose=True,
            ),
            indent=2,
            ensure_ascii=False,
        )
    )
    print()
    print("CrewAI Execution Scaffold")
    print(
        json.dumps(
            create_crewai_execution_scaffold(
                persona,
                tools=["case_lookup"],
                llm="mock-llm",
                verbose=True,
            ),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
