from __future__ import annotations

import unittest
from pathlib import Path

from pop import load_persona
from pop.integrations.langchain import (
    create_langchain_context_bundle,
    create_langchain_create_agent_kwargs,
    create_langchain_execution_bundle,
    create_langchain_middleware_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


class LangChainExecutionBundleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.persona = load_persona(LAWYER_PERSONA)

    def test_create_agent_kwargs_return_runtime_facing_dict(self) -> None:
        before = self.persona.to_dict()
        agent_kwargs = create_langchain_create_agent_kwargs(
            self.persona,
            tools=["case_lookup"],
            model="mock-model",
            system_prompt_prefix="Follow POP guidance.",
        )
        self.assertIsInstance(agent_kwargs, dict)
        self.assertEqual(agent_kwargs["model"], "mock-model")
        self.assertEqual(agent_kwargs["tools"], ["case_lookup"])
        self.assertIn("system_prompt", agent_kwargs)
        self.assertIn(self.persona.summary, agent_kwargs["system_prompt"])
        self.assertEqual(before, self.persona.to_dict())

    def test_context_bundle_returns_runtime_context_scaffold(self) -> None:
        before = self.persona.to_dict()
        context_bundle = create_langchain_context_bundle(self.persona)
        self.assertIsInstance(context_bundle, dict)
        self.assertEqual(context_bundle["kind"], "runtime_context")
        self.assertEqual(context_bundle["runtime"], "langchain")
        self.assertIn("persona", context_bundle)
        self.assertEqual(
            context_bundle["persona"]["persona_id"], self.persona.id
        )
        self.assertEqual(before, self.persona.to_dict())

    def test_middleware_bundle_returns_list(self) -> None:
        before = self.persona.to_dict()
        middleware_bundle = create_langchain_middleware_bundle(self.persona)
        self.assertIsInstance(middleware_bundle, list)
        self.assertTrue(middleware_bundle)
        self.assertIn("binding", middleware_bundle[0])
        self.assertIn(
            self.persona.boundaries[0],
            middleware_bundle[0]["binding"]["guardrail_instructions"],
        )
        self.assertEqual(before, self.persona.to_dict())

    def test_execution_bundle_contains_model_tools_prompt_context_and_middleware(
        self,
    ) -> None:
        before = self.persona.to_dict()
        execution_bundle = create_langchain_execution_bundle(
            self.persona,
            tools=["case_lookup"],
            model="mock-model",
            system_prompt_prefix="Follow POP guidance.",
        )
        self.assertIsInstance(execution_bundle, dict)
        self.assertEqual(execution_bundle["runtime"], "langchain")
        self.assertEqual(execution_bundle["target"], "create_agent")
        create_agent_kwargs = execution_bundle["create_agent_kwargs"]
        self.assertEqual(create_agent_kwargs["model"], "mock-model")
        self.assertEqual(create_agent_kwargs["tools"], ["case_lookup"])
        self.assertIn(self.persona.summary, create_agent_kwargs["system_prompt"])
        self.assertIn("context_bundle", execution_bundle)
        self.assertIn("middleware_bundle", execution_bundle)
        self.assertEqual(before, self.persona.to_dict())
