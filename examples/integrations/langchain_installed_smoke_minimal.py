from __future__ import annotations

import json
from pathlib import Path

from pop import (
    create_langchain_execution_bundle,
    load_persona,
    maybe_build_langchain_agent_spec,
)


ROOT = Path(__file__).resolve().parents[2]
PERSONA_PATH = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


def main() -> None:
    persona = load_persona(PERSONA_PATH)

    print("Main Entry Point Output")
    print(
        json.dumps(
            create_langchain_execution_bundle(persona),
            indent=2,
            ensure_ascii=False,
        )
    )
    print()
    print("Installed Optional-Dependency Spec Output")
    print(
        json.dumps(
            maybe_build_langchain_agent_spec(persona),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
