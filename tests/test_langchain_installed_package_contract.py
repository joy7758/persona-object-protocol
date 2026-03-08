from __future__ import annotations

import json
import subprocess
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path
from unittest.mock import patch

from pop import load_persona
from pop.integrations.langchain import maybe_build_langchain_agent_spec


ROOT = Path(__file__).resolve().parents[1]
LAWYER_PERSONA = ROOT / "fixtures" / "valid" / "lawyer_persona.json"


class LangChainInstalledPackageContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.persona = load_persona(LAWYER_PERSONA)

    def test_dependency_aware_spec_reports_langchain_when_available(self) -> None:
        if find_spec("langchain") is None:
            self.skipTest("langchain extra is not installed in this environment")
        spec = maybe_build_langchain_agent_spec(
            self.persona,
            tools=["case_lookup"],
            model="mock-model",
            system_prompt_prefix="Follow POP guidance.",
        )
        self.assertIsInstance(spec, dict)
        self.assertTrue(spec["langchain_available"])
        self.assertEqual(spec["runtime"], "langchain")
        self.assertEqual(spec["target"], "create_agent")
        self.assertEqual(spec["kind"], "langchain_execution_helper_spec")
        self.assertIn("create_agent_kwargs", spec)
        self.assertIn("context_bundle", spec)
        self.assertIn("middleware_bundle", spec)
        self.assertNotIn("agent", spec)

    def test_dependency_aware_spec_degrades_gracefully_without_langchain(self) -> None:
        with patch("pop.integrations.langchain.bindings.import_module", side_effect=ImportError):
            spec = maybe_build_langchain_agent_spec(
                self.persona,
                tools=["case_lookup"],
                model="mock-model",
                system_prompt_prefix="Follow POP guidance.",
            )

        self.assertIsInstance(spec, dict)
        self.assertFalse(spec["langchain_available"])
        self.assertIn("execution_bundle", spec)
        self.assertIn("note", spec)
        self.assertNotIn("agent", spec)

    def test_current_installed_environment_can_consume_contract_surface(self) -> None:
        if find_spec("langchain") is None:
            self.skipTest("langchain extra is not installed in this environment")
        script = f"""
from pop import load_persona
from pop.integrations.langchain import create_langchain_execution_bundle, maybe_build_langchain_agent_spec
persona = load_persona({str(LAWYER_PERSONA)!r})
bundle = create_langchain_execution_bundle(persona, tools=['case_lookup'], model='mock-model')
spec = maybe_build_langchain_agent_spec(persona, tools=['case_lookup'], model='mock-model')
print(json.dumps({{'bundle_target': bundle['target'], 'available': spec['langchain_available']}}, ensure_ascii=False))
"""
        result = subprocess.run(
            [sys.executable, "-c", "import json\n" + script],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout.strip())
        self.assertEqual(payload["bundle_target"], "create_agent")
        self.assertTrue(payload["available"])
