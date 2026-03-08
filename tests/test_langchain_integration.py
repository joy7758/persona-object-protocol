from __future__ import annotations

import unittest
from pathlib import Path

from pop import load_persona
from pop.integrations.langchain import (
    bind_langchain_context,
    bind_langchain_middleware,
    bind_langchain_prompt,
)


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


class LangChainIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.persona = load_persona(LAWYER_PERSONA)

    def test_prompt_binding_returns_non_empty_string(self) -> None:
        before = self.persona.to_dict()
        prompt = bind_langchain_prompt(self.persona)
        self.assertIsInstance(prompt, str)
        self.assertTrue(prompt.strip())
        self.assertIn(self.persona.summary, prompt)
        self.assertIn(self.persona.communication_style[0], prompt)
        self.assertIn(self.persona.boundaries[0], prompt)
        self.assertEqual(before, self.persona.to_dict())

    def test_context_binding_returns_runtime_facing_dict(self) -> None:
        before = self.persona.to_dict()
        context = bind_langchain_context(self.persona)
        self.assertIsInstance(context, dict)
        self.assertEqual(context["persona_summary"], self.persona.summary)
        self.assertIn(self.persona.communication_style[0], context["style_guidance"])
        self.assertIn(
            self.persona.boundaries[0], context["guardrail_instructions"]
        )
        self.assertEqual(before, self.persona.to_dict())

    def test_middleware_binding_returns_runtime_facing_dict(self) -> None:
        before = self.persona.to_dict()
        binding = bind_langchain_middleware(self.persona)
        self.assertIsInstance(binding, dict)
        self.assertEqual(binding["adapter"], "langchain")
        self.assertEqual(binding["system_framing"], self.persona.summary)
        self.assertIn(self.persona.communication_style[0], binding["style_guidance"])
        self.assertIn(
            self.persona.boundaries[0], binding["guardrail_instructions"]
        )
        self.assertEqual(before, self.persona.to_dict())
