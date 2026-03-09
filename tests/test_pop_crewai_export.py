import os
import tempfile
import unittest

from pop.adapter_crewai import export_crewai_agent_yaml, persona_to_crewai_config
from pop.loader import load_persona


class TestPOPCrewAIExport(unittest.TestCase):
    def test_load_persona(self):
        p = load_persona("personas/marketing_manager.json")
        self.assertEqual(p.role, "Marketing Manager")
        self.assertIn("strategic", p.traits)
        self.assertIn("analytics", p.tools)

    def test_persona_to_crewai_config(self):
        cfg = persona_to_crewai_config("personas/marketing_manager.json")
        self.assertEqual(cfg["role"], "Marketing Manager")
        self.assertIn("increase product awareness", cfg["goal"])
        self.assertIn("web_search", cfg["tools"])
        self.assertIn("Traits: strategic, data-driven, creative", cfg["backstory"])

    def test_export_crewai_agent_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "agent.yaml")
            export_crewai_agent_yaml("personas/marketing_manager.json", out)

            self.assertTrue(os.path.exists(out))

            with open(out, "r", encoding="utf-8") as f:
                text = f.read()

            self.assertIn('role: "Marketing Manager"', text)
            self.assertIn(
                'goal: "increase product awareness; design marketing campaigns"',
                text,
            )
            self.assertIn("tools:", text)
            self.assertIn('- "web_search"', text)

    def test_multiple_personas_load(self):
        for path, expected_role in [
            ("personas/marketing_manager.json", "Marketing Manager"),
            ("personas/engineer.json", "Software Engineer"),
            ("personas/designer.json", "Product Designer"),
        ]:
            p = load_persona(path)
            self.assertEqual(p.role, expected_role)


if __name__ == "__main__":
    unittest.main()
