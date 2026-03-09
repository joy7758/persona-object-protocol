from pathlib import Path
import importlib.util
import unittest

CONFIG_PATH = Path("examples/crewai_crewbase_demo/config/agents.yaml")
MODULE_PATH = Path("examples/crewai_crewbase_demo/crew_demo.py")


@unittest.skipUnless(importlib.util.find_spec("yaml"), "PyYAML not installed")
class TestPOPCrewAICrewBaseDemo(unittest.TestCase):
    def test_agents_yaml_exists(self):
        self.assertTrue(CONFIG_PATH.exists())

    def test_yaml_keys_match_expected_methods(self):
        import yaml

        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertEqual(
            sorted(data.keys()),
            sorted(["marketing_manager", "engineer", "designer"]),
        )

    def test_demo_class_methods_match_yaml_keys(self):
        import yaml

        spec = importlib.util.spec_from_file_location("crew_demo", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        demo = module.POPCrewDemo(data)
        methods = [
            name
            for name in ["marketing_manager", "engineer", "designer"]
            if hasattr(demo, name)
        ]

        self.assertEqual(sorted(methods), sorted(list(data.keys())))


if __name__ == "__main__":
    unittest.main()
