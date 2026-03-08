from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schema" / "pop-persona.schema.json"
SCHEMA_VERSIONS_PATH = ROOT / "schema" / "versions"


def load_pop_schema() -> dict:
    """Load the canonical POP persona schema from the repository."""

    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def get_schema_id() -> str:
    return str(load_pop_schema()["$id"])


def load_pop_schema_version(version: str) -> dict:
    """Load a versioned POP persona schema snapshot."""

    schema_path = SCHEMA_VERSIONS_PATH / f"pop-persona.{version}.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def list_available_schema_versions() -> list[str]:
    """List available versioned POP persona schema snapshots."""

    versions: list[str] = []
    for path in sorted(SCHEMA_VERSIONS_PATH.glob("pop-persona.v*.schema.json")):
        name = path.name
        versions.append(name.removeprefix("pop-persona.").removesuffix(".schema.json"))
    return versions
