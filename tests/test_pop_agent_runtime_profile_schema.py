import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


SCHEMA_PATH = Path("schema/profiles/pop-agent-runtime-profile.schema.json")


class TestPOPAgentRuntimeProfileSchema(unittest.TestCase):
    def test_schema_exists(self):
        self.assertTrue(SCHEMA_PATH.exists())

    def test_marketing_manager_valid(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)

        data = json.loads(
            Path("personas/marketing_manager.json").read_text(encoding="utf-8")
        )
        errors = list(validator.iter_errors(data))
        self.assertEqual(errors, [])

    def test_engineer_valid(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)

        data = json.loads(Path("personas/engineer.json").read_text(encoding="utf-8"))
        errors = list(validator.iter_errors(data))
        self.assertEqual(errors, [])

    def test_designer_valid(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)

        data = json.loads(Path("personas/designer.json").read_text(encoding="utf-8"))
        errors = list(validator.iter_errors(data))
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
