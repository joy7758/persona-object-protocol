from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schema" / "pop-persona.schema.json"


def load_pop_schema() -> dict:
    """Load the canonical POP persona schema from the repository."""

    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def get_schema_id() -> str:
    return str(load_pop_schema()["$id"])
