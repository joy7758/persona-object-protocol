from __future__ import annotations

import unittest
from pathlib import Path

from pop import load_persona
from pop.integrations.langchain import (
    create_langchain_agent_kwargs,
    create_langchain_execution_scaffold,
    create_langchain_middleware_scaffold,
)


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


class LangChainExecutionHelperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.persona = load_persona(LAWYER_PERSONA)

    def test_create_langchain_agent_kwargs_returns_runtime_dict(self) -> None:
        before = self.persona.to_dict()
        agent_kwargs = create_langchain_agent_kwargs(
            self.persona,
            tools=["case_lookup"],
            system_prompt_prefix="Follow POP persona guidance.",
            model="mock-model",
        )
        self.assertIsInstance(agent_kwargs, dict)
        self.assertIn("system_prompt", agent_kwargs)
        self.assertIn(self.persona.summary, agent_kwargs["system_prompt"])
        self.assertIn("context", agent_kwargs)
        self.assertIn("middleware", agent_kwargs)
        self.assertEqual(agent_kwargs["tools"], ["case_lookup"])
        self.assertEqual(agent_kwargs["model"], "mock-model")
        self.assertEqual(before, self.persona.to_dict())

    def test_create_langchain_execution_scaffold_returns_runtime_shape(self) -> None:
        before = self.persona.to_dict()
        scaffold = create_langchain_execution_scaffold(
            self.persona,
            tools=["case_lookup"],
            model="mock-model",
        )
        self.assertIsInstance(scaffold, dict)
        self.assertEqual(scaffold["runtime"], "langchain")
        self.assertEqual(scaffold["adapter"], "langchain")
        self.assertIn("agent_kwargs", scaffold)
        self.assertIn("context", scaffold)
        self.assertIn("middleware", scaffold)
        self.assertEqual(
            scaffold["agent_kwargs"]["tools"], ["case_lookup"]
        )
        self.assertEqual(before, self.persona.to_dict())

    def test_create_langchain_middleware_scaffold_returns_binding_surface(self) -> None:
        before = self.persona.to_dict()
        middleware = create_langchain_middleware_scaffold(self.persona)
        self.assertTrue(isinstance(middleware, (list, dict)))
        if isinstance(middleware, list):
            self.assertTrue(middleware)
            binding = middleware[0]["binding"]
        else:
            binding = middleware
        self.assertIn("system_framing", binding)
        self.assertIn("guardrail_instructions", binding)
        self.assertIn(self.persona.boundaries[0], binding["guardrail_instructions"])
        self.assertEqual(before, self.persona.to_dict())
