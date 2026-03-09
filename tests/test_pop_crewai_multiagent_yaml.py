import os
import tempfile
import unittest

from pop.adapter_crewai import export_crewai_agents_yaml


class TestPOPCrewAIMultiAgentYaml(unittest.TestCase):
    def test_export_multiagent_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "agents.yaml")
            export_crewai_agents_yaml(
                {
                    "marketing_manager": "personas/marketing_manager.json",
                    "engineer": "personas/engineer.json",
                    "designer": "personas/designer.json",
                },
                out,
            )

            self.assertTrue(os.path.exists(out))

            with open(out, "r", encoding="utf-8") as f:
                text = f.read()

            self.assertIn("marketing_manager:", text)
            self.assertIn("engineer:", text)
            self.assertIn("designer:", text)
            self.assertIn('role: "Marketing Manager"', text)
            self.assertIn('role: "Software Engineer"', text)
            self.assertIn('role: "Product Designer"', text)


if __name__ == "__main__":
    unittest.main()
