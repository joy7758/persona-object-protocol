from __future__ import annotations

import json
from pathlib import Path

from pop import load_persona
from pop.integrations.langchain import (
    create_langchain_execution_bundle,
    maybe_build_langchain_agent_spec,
)


ROOT = Path(__file__).resolve().parents[2]
PERSONA_PATH = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


def main() -> None:
    persona = load_persona(PERSONA_PATH)

    print("Main Execution Bundle")
    print(
        json.dumps(
            create_langchain_execution_bundle(
                persona,
                tools=["case_lookup"],
                model="mock-model",
                system_prompt_prefix="Installed contract surface",
            ),
            indent=2,
            ensure_ascii=False,
        )
    )
    print()
    print("Optional Dependency Spec")
    print(
        json.dumps(
            maybe_build_langchain_agent_spec(
                persona,
                tools=["case_lookup"],
                model="mock-model",
                system_prompt_prefix="Installed contract surface",
            ),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
