from __future__ import annotations

import unittest
from pathlib import Path

from pop import load_persona
from pop.integrations.crewai import (
    bind_crewai_agent_kwargs,
    create_crewai_agent_from_persona,
)


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


class CrewAIIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.persona = load_persona(LAWYER_PERSONA)

    def test_bind_crewai_agent_kwargs_returns_runtime_dict(self) -> None:
        before = self.persona.to_dict()
        kwargs = bind_crewai_agent_kwargs(self.persona)
        self.assertIsInstance(kwargs, dict)
        self.assertTrue(kwargs["role"])
        self.assertTrue(kwargs["goal"])
        self.assertTrue(kwargs["backstory"])
        self.assertIn(self.persona.summary, kwargs["role"])
        self.assertIn(self.persona.task_orientation[0], kwargs["goal"])
        self.assertEqual(before, self.persona.to_dict())

    def test_create_crewai_agent_from_persona_supports_passthrough_kwargs(self) -> None:
        before = self.persona.to_dict()
        agent = create_crewai_agent_from_persona(
            self.persona,
            tools=["case_lookup"],
            verbose=True,
        )
        self.assertIsInstance(agent, dict)
        self.assertEqual(agent["adapter"], "crewai")
        self.assertEqual(agent["persona_id"], self.persona.id)
        self.assertIn("role", agent)
        self.assertIn("goal", agent)
        self.assertIn("backstory", agent)
        self.assertEqual(agent["tools"], ["case_lookup"])
        self.assertTrue(agent["verbose"])
        self.assertNotIn("tools", self.persona.to_dict())
        self.assertEqual(before, self.persona.to_dict())
