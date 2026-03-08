from __future__ import annotations

import unittest
from pathlib import Path

from pop import load_persona
from pop.projections import project_to_crewai, project_to_langchain


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = (
    ROOT
    / "examples"
    / "cross-runtime-persona-portability"
    / "personas"
    / "lawyer_persona.json"
)


class SmokeTest(unittest.TestCase):
    def test_load_lawyer_persona(self) -> None:
        persona = load_persona(LAWYER_PERSONA)
        self.assertEqual(persona.id, "pop.persona.legal-analyst.v1")
        self.assertEqual(persona.name, "Legal Analysis Persona")

    def test_generate_runtime_projections(self) -> None:
        persona = load_persona(LAWYER_PERSONA)
        langchain_projection = project_to_langchain(persona)
        crewai_projection = project_to_crewai(persona)

        self.assertIn("system_framing", langchain_projection)
        self.assertIn("role", crewai_projection)
        self.assertTrue(langchain_projection["guardrail_instructions"])
        self.assertTrue(crewai_projection["output_expectations"])
