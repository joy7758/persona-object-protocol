from __future__ import annotations

import argparse
import json
import sys

from pop.io import load_persona, load_persona_data
from pop.projections import project_to_crewai, project_to_langchain
from pop.schema import get_schema_id, list_available_schema_versions
from pop.validate import PersonaValidationError, validate_persona, validate_persona_schema_dict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pop-inspect",
        description="Inspect a canonical POP persona object and print runtime projections.",
    )
    parser.add_argument("path", nargs="?", help="Path to a POP persona JSON file")
    parser.add_argument(
        "--strict-schema",
        action="store_true",
        help="Validate against the canonical JSON Schema instead of lightweight checks.",
    )
    parser.add_argument(
        "--show-schema-id",
        action="store_true",
        help="Print the object's declared $schema and the current SDK schema id.",
    )
    parser.add_argument(
        "--list-schema-versions",
        action="store_true",
        help="List available versioned schema snapshots and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_schema_versions:
        print("Available schema versions")
        for version in list_available_schema_versions():
            print(f"- {version}")
        return 0

    if not args.path:
        parser.error("the following arguments are required: path")

    try:
        raw_data = load_persona_data(args.path)
        persona = load_persona(args.path)
        if args.strict_schema:
            validate_persona_schema_dict(raw_data)
            validation_mode = "strict-json-schema"
        else:
            validate_persona(persona)
            validation_mode = "lightweight"
    except (FileNotFoundError, OSError, ValueError, PersonaValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Validation mode: {validation_mode}")
    print()
    if args.show_schema_id:
        print(f"Object $schema: {raw_data.get('$schema', '(not provided)')}")
        print(f"SDK current schema id: {get_schema_id()}")
        print()
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
