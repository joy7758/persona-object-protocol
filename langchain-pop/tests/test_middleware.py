from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from langchain_pop.middleware import POPMiddleware


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def knowledge_lookup(topic: str) -> str:
    """Look up a topic in a mock knowledge base."""
    return topic


def salary_estimator(role: str) -> str:
    """Estimate salary bands for a role."""
    return role


class POPMiddlewareTests(unittest.TestCase):
    def test_loads_v1_pop_object(self) -> None:
        middleware = POPMiddleware(FIXTURES / "mentor.v1.json")

        self.assertEqual(middleware.persona_state()["id"], "persona:mentor:langchain-fixture")
        self.assertEqual(middleware.persona_state()["role"], "mentor")
        self.assertEqual(middleware.persona_state()["status"], "active")

    def test_legacy_pop01_is_migrated(self) -> None:
        middleware = POPMiddleware(FIXTURES / "mentor.pop01.json")

        state = middleware.persona_state()
        self.assertEqual(state["kind"], "persona-object")
        self.assertEqual(state["role"], "skill-building mentor")
        self.assertTrue(state["version"].endswith("-migrated"))

    def test_boundaries_filter_tools(self) -> None:
        middleware = POPMiddleware(FIXTURES / "mentor.v1.json")

        allowed_tools, blocked_tools = middleware.filter_tools(
            [knowledge_lookup, salary_estimator]
        )

        self.assertEqual([tool.__name__ for tool in allowed_tools], ["knowledge_lookup"])
        self.assertEqual(len(blocked_tools), 1)
        self.assertEqual(blocked_tools[0]["tool_name"], "salary_estimator")
        self.assertEqual(blocked_tools[0]["boundary_key"], "tool.salary_estimator")


if __name__ == "__main__":
    unittest.main()
