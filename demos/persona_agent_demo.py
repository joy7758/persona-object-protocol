from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pop.persona_loader import load_all_personas


def run_demo() -> None:
    personas = load_all_personas(
        names=[
            "design_persona.json",
            "researcher_persona.json",
            "marketing_persona.json",
        ]
    )

    print("Loaded personas:")
    print("----------------")

    for persona in personas:
        print(persona.summary())
        print(" skills:", ", ".join(persona.skills))
        print()


if __name__ == "__main__":
    run_demo()
