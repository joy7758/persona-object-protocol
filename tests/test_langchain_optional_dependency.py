from __future__ import annotations

import unittest
from importlib.util import find_spec
from pathlib import Path

from pop import load_persona
from pop.integrations.langchain import maybe_build_langchain_agent_spec


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


class LangChainOptionalDependencyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.persona = load_persona(LAWYER_PERSONA)

    def test_optional_dependency_helper_stays_dependency_aware(self) -> None:
        before = self.persona.to_dict()
        spec = maybe_build_langchain_agent_spec(
            self.persona,
            tools=["case_lookup"],
            model="mock-model",
            system_prompt_prefix="Follow POP guidance.",
        )
        self.assertIsInstance(spec, dict)
        self.assertEqual(spec["runtime"], "langchain")
        self.assertEqual(spec["target"], "create_agent")
        langchain_installed = find_spec("langchain") is not None
        self.assertEqual(spec["langchain_available"], langchain_installed)
        if langchain_installed:
            self.assertIn("create_agent_kwargs", spec)
            self.assertIn("context_bundle", spec)
            self.assertIn("middleware_bundle", spec)
        else:
            self.assertIn("execution_bundle", spec)
            self.assertIn("note", spec)
        self.assertEqual(before, self.persona.to_dict())
