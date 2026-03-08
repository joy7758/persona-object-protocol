from __future__ import annotations

import unittest
from pathlib import Path

from pop import load_persona
from pop.integrations.crewai import (
    create_crewai_agent_kwargs,
    create_crewai_execution_scaffold,
)


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


class CrewAIExecutionHelperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.persona = load_persona(LAWYER_PERSONA)

    def test_create_crewai_agent_kwargs_returns_runtime_dict(self) -> None:
        before = self.persona.to_dict()
        agent_kwargs = create_crewai_agent_kwargs(
            self.persona,
            tools=["case_lookup"],
            llm="mock-llm",
            verbose=True,
        )
        self.assertIsInstance(agent_kwargs, dict)
        self.assertIn("role", agent_kwargs)
        self.assertIn("goal", agent_kwargs)
        self.assertIn("backstory", agent_kwargs)
        self.assertEqual(agent_kwargs["tools"], ["case_lookup"])
        self.assertEqual(agent_kwargs["llm"], "mock-llm")
        self.assertTrue(agent_kwargs["verbose"])
        self.assertNotIn("tools", self.persona.to_dict())
        self.assertEqual(before, self.persona.to_dict())

    def test_create_crewai_execution_scaffold_returns_runtime_shape(self) -> None:
        before = self.persona.to_dict()
        scaffold = create_crewai_execution_scaffold(
            self.persona,
            tools=["case_lookup"],
            llm="mock-llm",
            verbose=True,
        )
        self.assertIsInstance(scaffold, dict)
        self.assertEqual(scaffold["runtime"], "crewai")
        self.assertEqual(scaffold["adapter"], "crewai")
        self.assertIn("agent_kwargs", scaffold)
        self.assertEqual(
            scaffold["agent_kwargs"]["tools"], ["case_lookup"]
        )
        self.assertEqual(
            scaffold["agent_kwargs"]["goal"].splitlines()[0],
            self.persona.task_orientation[0],
        )
        self.assertEqual(before, self.persona.to_dict())
