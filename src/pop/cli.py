from __future__ import annotations

import argparse
import json
import sys

from pop.io import load_persona
from pop.projections import project_to_crewai, project_to_langchain
from pop.validate import PersonaValidationError, validate_persona


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pop-inspect",
        description="Inspect a canonical POP persona object and print runtime projections.",
    )
    parser.add_argument("path", help="Path to a POP persona JSON file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        persona = load_persona(args.path)
        validate_persona(persona)
    except (FileNotFoundError, OSError, ValueError, PersonaValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = {
        "id": persona.id,
        "version": persona.version,
        "name": persona.name,
        "summary": persona.summary,
    }

    print("Persona Summary")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print()
    print("LangChain Projection")
    print(json.dumps(project_to_langchain(persona), indent=2, ensure_ascii=False))
    print()
    print("CrewAI Projection")
    print(json.dumps(project_to_crewai(persona), indent=2, ensure_ascii=False))
    return 0
