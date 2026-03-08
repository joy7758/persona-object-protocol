from __future__ import annotations

import json
from pathlib import Path

from pop import create_langchain_execution_bundle, load_persona


root = Path(__file__).resolve().parents[2]
persona = load_persona(root / "fixtures" / "valid" / "lawyer_persona.json")
bundle = create_langchain_execution_bundle(persona)

print("create_agent_kwargs")
print(json.dumps(bundle["create_agent_kwargs"], indent=2, ensure_ascii=False))
print()
print("context_bundle")
print(json.dumps(bundle["context_bundle"], indent=2, ensure_ascii=False))
print()
print("middleware_bundle")
print(json.dumps(bundle["middleware_bundle"], indent=2, ensure_ascii=False))
