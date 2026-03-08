from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schema" / "pop-persona.schema.json"
SCHEMA_VERSIONS_PATH = ROOT / "schema" / "versions"


def _packaged_schema_root():
    return files("pop") / "resources" / "schema"


def _load_json_resource(resource) -> dict:
    return json.loads(resource.read_text(encoding="utf-8"))


def load_pop_schema() -> dict:
    """Load the canonical POP persona schema from the repository."""

    packaged_path = _packaged_schema_root() / "pop-persona.schema.json"
    try:
        return _load_json_resource(packaged_path)
    except FileNotFoundError:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def get_schema_id() -> str:
    return str(load_pop_schema()["$id"])


def load_pop_schema_version(version: str) -> dict:
    """Load a versioned POP persona schema snapshot."""

    file_name = f"pop-persona.{version}.schema.json"
    packaged_path = _packaged_schema_root() / "versions" / file_name
    try:
        return _load_json_resource(packaged_path)
    except FileNotFoundError:
        schema_path = SCHEMA_VERSIONS_PATH / file_name
        return json.loads(schema_path.read_text(encoding="utf-8"))


def list_available_schema_versions() -> list[str]:
    """List available versioned POP persona schema snapshots."""

    versions: list[str] = []
    packaged_versions_path = _packaged_schema_root() / "versions"
    try:
        paths = sorted(packaged_versions_path.iterdir(), key=lambda path: path.name)
    except FileNotFoundError:
        paths = sorted(SCHEMA_VERSIONS_PATH.glob("pop-persona.v*.schema.json"))

    for path in paths:
        name = path.name
        if not name.startswith("pop-persona.v") or not name.endswith(".schema.json"):
            continue
        versions.append(name.removeprefix("pop-persona.").removesuffix(".schema.json"))
    return versions
