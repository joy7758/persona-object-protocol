from __future__ import annotations

import unittest
from pathlib import Path

from pop import CrewAIAdapter, LangChainAdapter, load_persona
from pop.projections import project_to_crewai, project_to_langchain


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


class AdapterClassTest(unittest.TestCase):
    def setUp(self) -> None:
        self.persona = load_persona(LAWYER_PERSONA)

    def test_langchain_adapter_returns_runtime_dict(self) -> None:
        adapted = LangChainAdapter().adapt(self.persona)
        self.assertIsInstance(adapted, dict)
        self.assertTrue(
            {
                "system_framing",
                "style_guidance",
                "response_policy_hints",
                "guardrail_instructions",
                "output_format_hints",
            }.issubset(adapted)
        )

    def test_crewai_adapter_returns_runtime_dict(self) -> None:
        adapted = CrewAIAdapter().adapt(self.persona)
        self.assertIsInstance(adapted, dict)
        self.assertTrue(
            {
                "role",
                "goal",
                "backstory",
                "behavioral_constraints",
                "output_expectations",
            }.issubset(adapted)
        )

    def test_adapters_do_not_mutate_persona(self) -> None:
        before = self.persona.to_dict()
        LangChainAdapter().adapt(self.persona)
        CrewAIAdapter().adapt(self.persona)
        self.assertEqual(before, self.persona.to_dict())

    def test_adapter_outputs_do_not_include_non_persona_bindings(self) -> None:
        for adapted in (
            LangChainAdapter().adapt(self.persona),
            CrewAIAdapter().adapt(self.persona),
        ):
            self.assertNotIn("tools", adapted)
            self.assertNotIn("memory", adapted)
            self.assertNotIn("permissions", adapted)

    def test_projection_functions_align_with_adapter_classes(self) -> None:
        self.assertEqual(
            project_to_langchain(self.persona),
            LangChainAdapter().adapt(self.persona),
        )
        self.assertEqual(
            project_to_crewai(self.persona),
            CrewAIAdapter().adapt(self.persona),
        )
