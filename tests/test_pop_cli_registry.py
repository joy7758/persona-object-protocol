from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pop_protocol.cli import main


class TestPopCliRegistry(unittest.TestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(list(argv))
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_resolve_command(self) -> None:
        code, output, _ = self.run_cli("resolve", "pop:marketing_manager_v1")
        self.assertEqual(code, 0)
        self.assertIn("personas/marketing_manager.json", output)

    def test_validate_id_command(self) -> None:
        code, output, _ = self.run_cli("validate-id", "pop:marketing_manager_v1")
        self.assertEqual(code, 0)
        self.assertIn('"valid": true', output.lower())

    def test_project_id_command(self) -> None:
        code, output, _ = self.run_cli(
            "project-id",
            "pop:marketing_manager_v1",
            "--runtime",
            "agent",
        )
        self.assertEqual(code, 0)
        self.assertIn('"projection_type": "agent"', output)


if __name__ == "__main__":
    unittest.main()
