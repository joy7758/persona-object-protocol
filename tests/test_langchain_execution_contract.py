from __future__ import annotations

import unittest
from pathlib import Path

from pop import load_persona
from pop.integrations.langchain import (
    create_langchain_context_bundle,
    create_langchain_create_agent_kwargs,
    create_langchain_agent_kwargs,
    create_langchain_execution_bundle,
    create_langchain_execution_scaffold,
    create_langchain_middleware_bundle,
    create_langchain_middleware_scaffold,
)


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


class LangChainExecutionContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.persona = load_persona(LAWYER_PERSONA)

    def test_execution_bundle_is_main_entrypoint(self) -> None:
        bundle = create_langchain_execution_bundle(
            self.persona,
            tools=["case_lookup"],
            model="mock-model",
        )

        self.assertIsInstance(bundle, dict)
        self.assertIn("create_agent_kwargs", bundle)
        self.assertIn("context_bundle", bundle)
        self.assertIn("middleware_bundle", bundle)
        self.assertIn("metadata", bundle)
        self.assertEqual(bundle["metadata"]["entrypoint"], "create_langchain_execution_bundle")
        self.assertEqual(bundle["metadata"]["surface"], "execution_contract")

    def test_create_agent_kwargs_contract_stays_runtime_facing(self) -> None:
        before = self.persona.to_dict()
        agent_kwargs = create_langchain_create_agent_kwargs(
            self.persona,
            tools=["case_lookup"],
            model="mock-model",
            system_prompt_prefix="Follow POP guidance.",
        )
        self.assertEqual(agent_kwargs["model"], "mock-model")
        self.assertEqual(agent_kwargs["tools"], ["case_lookup"])
        self.assertIn(self.persona.summary, agent_kwargs["system_prompt"])
        self.assertIn(self.persona.communication_style[0], agent_kwargs["system_prompt"])
        self.assertIn(self.persona.boundaries[0], agent_kwargs["system_prompt"])
        self.assertNotIn("tools", self.persona.to_dict())
        self.assertEqual(before, self.persona.to_dict())

    def test_context_bundle_contract_stays_runtime_context_only(self) -> None:
        before = self.persona.to_dict()
        context_bundle = create_langchain_context_bundle(self.persona)
        self.assertEqual(context_bundle["kind"], "runtime_context")
        self.assertEqual(context_bundle["runtime"], "langchain")
        self.assertIn("persona", context_bundle)
        self.assertNotIn("system_prompt", context_bundle)
        self.assertNotIn("tools", context_bundle)
        self.assertEqual(before, self.persona.to_dict())

    def test_middleware_bundle_contract_stays_sequence_and_guardrail_facing(self) -> None:
        before = self.persona.to_dict()
        middleware_bundle = create_langchain_middleware_bundle(self.persona)
        self.assertIsInstance(middleware_bundle, list)
        self.assertTrue(middleware_bundle)
        binding = middleware_bundle[0]["binding"]
        self.assertIn("system_framing", binding)
        self.assertIn("style_guidance", binding)
        self.assertIn("guardrail_instructions", binding)
        self.assertIn(self.persona.boundaries[0], binding["guardrail_instructions"])
        self.assertEqual(before, self.persona.to_dict())

    def test_compatibility_helpers_remain_wrappers(self) -> None:
        old_agent_kwargs = create_langchain_agent_kwargs(
            self.persona,
            tools=["case_lookup"],
            model="mock-model",
            system_prompt_prefix="Follow POP guidance.",
        )
        new_agent_kwargs = create_langchain_create_agent_kwargs(
            self.persona,
            tools=["case_lookup"],
            model="mock-model",
            system_prompt_prefix="Follow POP guidance.",
        )
        bundle = create_langchain_execution_bundle(
            self.persona,
            tools=["case_lookup"],
            model="mock-model",
        )
        old_scaffold = create_langchain_execution_scaffold(
            self.persona,
            tools=["case_lookup"],
            model="mock-model",
        )
        old_middleware = create_langchain_middleware_scaffold(self.persona)
        new_middleware = create_langchain_middleware_bundle(self.persona)

        self.assertEqual(old_agent_kwargs["system_prompt"], new_agent_kwargs["system_prompt"])
        self.assertEqual(old_agent_kwargs["tools"], new_agent_kwargs["tools"])
        self.assertEqual(old_scaffold["bundle"], bundle)
        self.assertEqual(old_middleware, new_middleware)
