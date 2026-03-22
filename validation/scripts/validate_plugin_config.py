#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / "plugin_config.example.json"
DEFAULT_SCHEMA_PATH = ROOT / "plugin_config.schema.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a plugin config file against the repository schema."
    )
    parser.add_argument(
        "config_path",
        nargs="?",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the plugin config file to validate.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Path to the plugin config schema file.",
    )
    args = parser.parse_args()

    config_path = args.config_path.resolve()
    schema_path = args.schema.resolve()
    schema = load_json(schema_path)
    payload = load_json(config_path)

    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        first_error = errors[0]
        path = ".".join(str(part) for part in first_error.absolute_path) or "<root>"
        raise ValueError(f"{config_path}: invalid at {path}: {first_error.message}")

    print(f"Validated {config_path.relative_to(ROOT)} against {schema_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
