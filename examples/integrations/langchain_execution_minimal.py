from __future__ import annotations

import json
from pathlib import Path

from pop import load_persona
from pop.integrations.langchain import (
    create_langchain_agent_kwargs,
    create_langchain_execution_scaffold,
    create_langchain_middleware_scaffold,
)


ROOT = Path(__file__).resolve().parents[2]
PERSONA_PATH = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


def main() -> None:
    persona = load_persona(PERSONA_PATH)
    print("LangChain Agent Kwargs")
    print(
        json.dumps(
            create_langchain_agent_kwargs(
                persona,
                tools=["case_lookup"],
                system_prompt_prefix="Execution scaffold",
                model="mock-model",
            ),
            indent=2,
            ensure_ascii=False,
        )
    )
    print()
    print("LangChain Execution Scaffold")
    print(
        json.dumps(
            create_langchain_execution_scaffold(
                persona,
                tools=["case_lookup"],
                model="mock-model",
            ),
            indent=2,
            ensure_ascii=False,
        )
    )
    print()
    print("LangChain Middleware Scaffold")
    print(
        json.dumps(
            create_langchain_middleware_scaffold(persona),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
