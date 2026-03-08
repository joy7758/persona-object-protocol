from __future__ import annotations

import unittest
from pathlib import Path

from pop import (
    create_langchain_execution_bundle,
    load_persona,
    maybe_build_langchain_agent_spec,
)


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


class LangChainMinimalAdoptionPathTest(unittest.TestCase):
    def setUp(self) -> None:
        self.persona = load_persona(LAWYER_PERSONA)

    def test_main_entrypoint_supports_minimal_adoption_path(self) -> None:
        before = self.persona.to_dict()
        bundle = create_langchain_execution_bundle(self.persona)

        self.assertIn("create_agent_kwargs", bundle)
        self.assertIn("context_bundle", bundle)
        self.assertIn("middleware_bundle", bundle)
        self.assertEqual(bundle["metadata"]["entrypoint"], "create_langchain_execution_bundle")
        self.assertEqual(before, self.persona.to_dict())

    def test_dependency_aware_spec_gracefully_supports_first_smoke(self) -> None:
        before = self.persona.to_dict()
        spec = maybe_build_langchain_agent_spec(self.persona)

        self.assertIsInstance(spec, dict)
        self.assertIn("langchain_available", spec)
        if spec["langchain_available"]:
            self.assertEqual(spec["target"], "create_agent")
            self.assertIn("create_agent_kwargs", spec)
            self.assertIn("context_bundle", spec)
            self.assertIn("middleware_bundle", spec)
        else:
            self.assertEqual(spec["kind"], "langchain_execution_scaffold")
            self.assertIn("execution_bundle", spec)
        self.assertEqual(before, self.persona.to_dict())
