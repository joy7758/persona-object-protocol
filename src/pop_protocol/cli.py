from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pop_protocol import __version__
from pop_protocol.core import (
    default_migration_path,
    ensure_v1_object,
    load_json,
    project_object,
    resolve_input_path,
    validate_object,
    write_json,
)


def _resolve_persona_or_exit(persona_ref: str) -> Path:
    try:
        from pop.registry import resolve_persona
    except Exception as exc:  # pragma: no cover
        raise SystemExit("Persona registry support is unavailable in this environment.") from exc

    path = resolve_persona(persona_ref)
    if path is None:
        raise SystemExit(f"Persona not found: {persona_ref}")
    return Path(path)


def _project_runtime_profile(persona: Any, runtime: str) -> str | dict[str, Any]:
    if runtime == "prompt":
        segments = [f"You are a {persona.role}."]
        if getattr(persona, "traits", None):
            segments.append(f"Traits: {', '.join(persona.traits)}.")
        if getattr(persona, "goals", None):
            segments.append(f"Goals: {'; '.join(persona.goals)}.")
        if getattr(persona, "style", None):
            segments.append(f"Communication style: {persona.style}.")
        if getattr(persona, "memory_scope", None):
            segments.append(f"Memory scope: {persona.memory_scope}.")
        return " ".join(segments)

    if runtime == "app":
        return {
            "projection_type": "app",
            "role_model": {
                "persona_id": persona.persona_id,
                "name": persona.name,
                "role": persona.role,
                "traits": list(persona.traits),
                "goals": list(persona.goals),
                "tools": list(persona.tools),
                "communication_style": persona.style,
                "memory_scope": persona.memory_scope,
            },
        }

    if runtime == "agent":
        return {
            "projection_type": "agent",
            "runtime_contract": {
                "persona_ref": {
                    "persona_id": persona.persona_id,
                    "name": persona.name,
                },
                "behavior_contract": {
                    "role": persona.role,
                    "traits": list(persona.traits),
                    "goals": list(persona.goals),
                },
                "tool_contract": list(persona.tools),
                "communication_style": persona.style,
                "memory_scope": persona.memory_scope,
            },
        }

    raise ValueError(f"Unsupported runtime: {runtime}")


def print_error_lines(lines: list[str]) -> None:
    for line in lines:
        print(f"ERROR {line}", file=sys.stderr)


def handle_validate(args: argparse.Namespace) -> int:
    path = resolve_input_path(args.file)
    payload = load_json(path)
    report = validate_object(payload, schema_mode=args.schema)

    if args.json_output:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=True))
        return 0 if report.ok else 1

    if report.schema_errors:
        print("ERROR schema invalid")
        print_error_lines(report.schema_errors)
        return 1

    print(f"OK schema valid ({report.schema_kind})")

    if report.schema_kind == "v1":
        if report.lifecycle_errors:
            print("ERROR lifecycle invalid")
            print_error_lines(report.lifecycle_errors)
        else:
            print("OK lifecycle valid")

        if report.boundary_errors:
            print("ERROR boundaries invalid")
            print_error_lines(report.boundary_errors)
        else:
            print("OK boundaries valid")
    else:
        print("OK legacy POP 0.1 object recognized")

    if report.warnings:
        for warning in report.warnings:
            print(f"WARN {warning}")

    return 0 if report.ok else 1


def emit_projection(output: str | dict[str, Any], output_path: Path | None) -> None:
    if output_path is None:
        if isinstance(output, str):
            print(output)
        else:
            print(json.dumps(output, indent=2, ensure_ascii=True))
        return

    if isinstance(output, str):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    else:
        write_json(output_path, output)
    print(output_path.as_posix())


def handle_project(args: argparse.Namespace) -> int:
    path = resolve_input_path(args.file)
    payload = load_json(path)
    v1_payload, migrated = ensure_v1_object(payload, source_label=path.as_posix())
    projection = project_object(v1_payload, runtime=args.runtime)

    if migrated:
        print("WARN legacy POP 0.1 input was auto-migrated to POP v1.0 before projection", file=sys.stderr)

    output_path = Path(args.output).expanduser() if args.output else None
    emit_projection(projection, output_path)
    return 0


def handle_migrate(args: argparse.Namespace) -> int:
    path = resolve_input_path(args.file)
    payload = load_json(path)
    report = validate_object(payload, schema_mode="pop-0.1")
    if not report.ok:
        print("ERROR legacy POP 0.1 object is invalid", file=sys.stderr)
        print_error_lines(report.schema_errors)
        return 1

    migrated_payload, _ = ensure_v1_object(payload, source_label=path.as_posix())
    output_path = Path(args.output).expanduser() if args.output else default_migration_path(path)
    write_json(output_path, migrated_payload)
    print(output_path.as_posix())
    return 0


def handle_resolve(args: argparse.Namespace) -> int:
    path = _resolve_persona_or_exit(args.persona_ref)
    print(path.as_posix())
    return 0


def handle_validate_id(args: argparse.Namespace) -> int:
    try:
        from pop.loader import validate_persona as validate_runtime_persona
    except Exception as exc:  # pragma: no cover
        raise SystemExit("Persona loader support is unavailable in this environment.") from exc

    path = _resolve_persona_or_exit(args.persona_ref)
    result = validate_runtime_persona(path)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result.get("valid") else 1


def handle_project_id(args: argparse.Namespace) -> int:
    try:
        from pop.registry import load_persona_by_id
    except Exception as exc:  # pragma: no cover
        raise SystemExit("Persona registry support is unavailable in this environment.") from exc

    persona = load_persona_by_id(args.persona_ref)
    projection = _project_runtime_profile(persona, runtime=args.runtime)
    output_path = Path(args.output).expanduser() if args.output else None
    emit_projection(projection, output_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pop", description="POP reference CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a POP object")
    validate_parser.add_argument("file", help="Path to a POP object JSON file")
    validate_parser.add_argument(
        "--schema",
        choices=["auto", "v1", "pop-0.1"],
        default="auto",
        help="Schema mode to use for validation",
    )
    validate_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit the validation report as JSON",
    )
    validate_parser.set_defaults(handler=handle_validate)

    project_parser = subparsers.add_parser("project", help="Project a POP object into a runtime view")
    project_parser.add_argument("file", help="Path to a POP object JSON file")
    project_parser.add_argument(
        "--runtime",
        choices=["prompt", "app", "agent"],
        default="prompt",
        help="Projection target runtime",
    )
    project_parser.add_argument(
        "-o",
        "--output",
        help="Optional output path for the projection result",
    )
    project_parser.set_defaults(handler=handle_project)

    resolve_parser = subparsers.add_parser(
        "resolve",
        help="Resolve persona ref to local file path",
    )
    resolve_parser.add_argument("persona_ref")
    resolve_parser.set_defaults(handler=handle_resolve)

    validate_id_parser = subparsers.add_parser(
        "validate-id",
        help="Validate persona by persona ref",
    )
    validate_id_parser.add_argument("persona_ref")
    validate_id_parser.set_defaults(handler=handle_validate_id)

    project_id_parser = subparsers.add_parser(
        "project-id",
        help="Project persona by persona ref",
    )
    project_id_parser.add_argument("persona_ref")
    project_id_parser.add_argument(
        "--runtime",
        choices=["prompt", "app", "agent"],
        required=True,
        help="Projection target runtime",
    )
    project_id_parser.add_argument(
        "-o",
        "--output",
        help="Optional output path for the projection result",
    )
    project_id_parser.set_defaults(handler=handle_project_id)

    migrate_parser = subparsers.add_parser(
        "migrate-pop01",
        help="Migrate a legacy POP 0.1 object into the canonical POP v1.0 binding",
    )
    migrate_parser.add_argument("file", help="Path to a legacy POP 0.1 JSON file")
    migrate_parser.add_argument(
        "-o",
        "--output",
        help="Optional output path for the migrated POP v1.0 object",
    )
    migrate_parser.set_defaults(handler=handle_migrate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
