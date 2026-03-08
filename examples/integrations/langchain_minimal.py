from __future__ import annotations

import json
from pathlib import Path

from pop import load_persona
from pop.integrations.langchain import (
    bind_langchain_context,
    bind_langchain_middleware,
    bind_langchain_prompt,
)


ROOT = Path(__file__).resolve().parents[2]
PERSONA_PATH = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


def main() -> None:
    persona = load_persona(PERSONA_PATH)
    print("LangChain Prompt Binding")
    print(bind_langchain_prompt(persona))
    print()
    print("LangChain Context Binding")
    print(json.dumps(bind_langchain_context(persona), indent=2, ensure_ascii=False))
    print()
    print("LangChain Middleware Binding")
    print(
        json.dumps(
            bind_langchain_middleware(persona), indent=2, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
