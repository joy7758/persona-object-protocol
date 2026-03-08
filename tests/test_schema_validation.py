from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

from pop import validate_persona_schema_dict
from pop.validate import PersonaValidationError


ROOT = Path(__file__).resolve().parents[1]
VALID_FIXTURES_DIR = ROOT / "fixtures" / "valid"
INVALID_FIXTURES_DIR = ROOT / "fixtures" / "invalid"
HAS_JSONSCHEMA = importlib.util.find_spec("jsonschema") is not None


@unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema is not installed")
class SchemaValidationTest(unittest.TestCase):
    def test_all_valid_fixtures_pass_strict_schema(self) -> None:
        fixture_paths = sorted(VALID_FIXTURES_DIR.glob("*.json"))
        self.assertTrue(fixture_paths, "No valid fixtures were found.")
        for path in fixture_paths:
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                validate_persona_schema_dict(payload)

    def test_all_invalid_fixtures_fail_strict_schema(self) -> None:
        fixture_paths = sorted(INVALID_FIXTURES_DIR.glob("*.json"))
        self.assertTrue(fixture_paths, "No invalid fixtures were found.")
        for path in fixture_paths:
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                with self.assertRaises(PersonaValidationError):
                    validate_persona_schema_dict(payload)
