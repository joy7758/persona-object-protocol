from __future__ import annotations

import unittest
from pathlib import Path

from pop import list_available_schema_versions, load_persona, load_pop_schema
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
    def test_schema_versions_are_available(self) -> None:
        self.assertIn("v0.1.0", list_available_schema_versions())

    def test_current_schema_is_loadable(self) -> None:
        schema = load_pop_schema()
        self.assertEqual(schema["title"], "POP Persona Object")
        self.assertIn("$defs", schema)

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
