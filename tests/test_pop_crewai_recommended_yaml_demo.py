from pathlib import Path
import importlib.util
import unittest

CONFIG_PATH = Path("examples/crewai_config_demo/config/agents.yaml")


@unittest.skipUnless(importlib.util.find_spec("yaml"), "PyYAML not installed")
class TestPOPCrewAIRecommendedYamlDemo(unittest.TestCase):
    def test_agents_yaml_exists(self):
        self.assertTrue(CONFIG_PATH.exists())

    def test_agents_yaml_structure(self):
        import yaml

        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertIn("marketing_manager", data)
        self.assertIn("engineer", data)
        self.assertIn("designer", data)

        for key in ["marketing_manager", "engineer", "designer"]:
            self.assertIn("role", data[key])
            self.assertIn("goal", data[key])
            self.assertIn("backstory", data[key])


if __name__ == "__main__":
    unittest.main()
