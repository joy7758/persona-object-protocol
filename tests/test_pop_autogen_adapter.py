import unittest

from pop.adapter_autogen import (
    agent_from_persona,
    assistant_agent_from_persona,
    persona_to_autogen_config,
)


class TestPOPAutoGenAdapter(unittest.TestCase):
    def test_persona_to_autogen_config(self):
        cfg = persona_to_autogen_config("personas/marketing_manager.json", model="gpt-4o")
        self.assertEqual(cfg["name"], "Marketing Manager")
        self.assertIn("You are a Marketing Manager.", cfg["system_message"])
        self.assertIn("web_search", cfg["tools"])
        self.assertEqual(cfg["metadata"]["persona_id"], "marketing_manager_v1")

    def test_assistant_agent_from_persona_without_autogen_or_model_client(self):
        result = assistant_agent_from_persona(
            "personas/marketing_manager.json",
            model_client=None,
        )
        self.assertIsInstance(result, dict)
        self.assertIn(result["status"], {"AUTOGEN_NOT_INSTALLED", "MODEL_CLIENT_REQUIRED"})

    def test_deprecated_alias(self):
        result = agent_from_persona("personas/marketing_manager.json", model="gpt-4o")
        self.assertEqual(result["status"], "DEPRECATED_ALIAS")
        self.assertIn("Use assistant_agent_from_persona", result["message"])


if __name__ == "__main__":
    unittest.main()
