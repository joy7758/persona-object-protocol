from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

from pop import validate_persona_schema_dict
from pop.validate import PersonaValidationError


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = (
    ROOT
    / "examples"
    / "cross-runtime-persona-portability"
    / "personas"
    / "lawyer_persona.json"
)
HAS_JSONSCHEMA = importlib.util.find_spec("jsonschema") is not None


@unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema is not installed")
class SchemaValidationTest(unittest.TestCase):
    def test_example_persona_passes_strict_schema(self) -> None:
        payload = json.loads(LAWYER_PERSONA.read_text(encoding="utf-8"))
        validate_persona_schema_dict(payload)

    def test_invalid_persona_fails_strict_schema(self) -> None:
        invalid_payload = {
            "version": "0.1-draft",
            "name": "Broken Persona",
            "summary": "Missing id and list fields.",
            "traits": [],
            "communication_style": [],
            "task_orientation": [],
            "boundaries": [],
            "preferred_outputs": [],
            "metadata": {}
        }

        with self.assertRaises(PersonaValidationError):
            validate_persona_schema_dict(invalid_payload)
