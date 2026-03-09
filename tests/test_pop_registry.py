import unittest

from pop.loader import validate_persona
from pop.registry import list_personas, load_persona_by_id, resolve_persona


class TestPOPRegistry(unittest.TestCase):
    def test_list_personas(self):
        personas = list_personas()
        self.assertTrue(any("marketing_manager.json" in path for path in personas))
        self.assertTrue(any("engineer.json" in path for path in personas))
        self.assertTrue(any("designer.json" in path for path in personas))

    def test_resolve_persona(self):
        path = resolve_persona("marketing_manager_v1")
        self.assertIsNotNone(path)
        self.assertIn("marketing_manager.json", path)

    def test_load_persona_by_id(self):
        persona = load_persona_by_id("marketing_manager_v1")
        self.assertEqual(persona.role, "Marketing Manager")

    def test_validate_persona(self):
        result = validate_persona("personas/marketing_manager.json")
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main()
