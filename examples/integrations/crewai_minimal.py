from __future__ import annotations

import json
from pathlib import Path

from pop import load_persona
from pop.integrations.crewai import (
    bind_crewai_agent_kwargs,
    create_crewai_agent_from_persona,
)


ROOT = Path(__file__).resolve().parents[2]
PERSONA_PATH = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


def main() -> None:
    persona = load_persona(PERSONA_PATH)
    print("CrewAI Agent Kwargs")
    print(json.dumps(bind_crewai_agent_kwargs(persona), indent=2, ensure_ascii=False))
    print()
    print("CrewAI Agent Scaffold")
    print(
        json.dumps(
            create_crewai_agent_from_persona(
                persona,
                tools=["case_lookup"],
                verbose=True,
            ),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
