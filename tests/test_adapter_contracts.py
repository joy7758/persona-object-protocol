from __future__ import annotations

import unittest
from pathlib import Path

from pop import load_persona
from pop.projections import project_to_crewai, project_to_langchain


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


class AdapterContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.persona = load_persona(LAWYER_PERSONA)

    def test_langchain_projection_preserves_summary_intent(self) -> None:
        projection = project_to_langchain(self.persona)
        self.assertEqual(
            set(projection),
            {
                "system_framing",
                "style_guidance",
                "response_policy_hints",
                "guardrail_instructions",
                "output_format_hints",
            },
        )
        self.assertIn(self.persona.summary, projection["system_framing"])

    def test_crewai_projection_preserves_role_goal_shape(self) -> None:
        projection = project_to_crewai(self.persona)
        self.assertEqual(
            set(projection),
            {
                "role",
                "goal",
                "backstory",
                "behavioral_constraints",
                "output_expectations",
            },
        )
        self.assertTrue(projection["role"])
        self.assertTrue(projection["goal"])
        for item in self.persona.task_orientation:
            self.assertIn(item, projection["goal"])

    def test_projections_do_not_mutate_canonical_persona(self) -> None:
        before = self.persona.to_dict()
        project_to_langchain(self.persona)
        project_to_crewai(self.persona)
        self.assertEqual(before, self.persona.to_dict())

    def test_projection_outputs_are_runtime_facing_not_core_replacements(self) -> None:
        for projection in (
            project_to_langchain(self.persona),
            project_to_crewai(self.persona),
        ):
            self.assertIsInstance(projection, dict)
            self.assertNotIn("id", projection)
            self.assertNotIn("version", projection)
            self.assertNotIn("summary", projection)
            self.assertNotIn("tools", projection)
            self.assertNotIn("memory", projection)
            self.assertNotIn("permissions", projection)
