from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from langchain_pop.agent import create_pop_agent


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def knowledge_lookup(topic: str) -> str:
    """Look up a topic in a mock knowledge base."""
    return topic


class CreatePopAgentTests(unittest.TestCase):
    def test_returns_compiled_state_graph(self) -> None:
        model = FakeListChatModel(responses=["Acknowledged."])

        agent = create_pop_agent(
            pop_source=FIXTURES / "mentor.v1.json",
            model=model,
            tools=[knowledge_lookup],
            name="langchain_pop_test_agent",
        )

        self.assertEqual(type(agent).__name__, "CompiledStateGraph")


if __name__ == "__main__":
    unittest.main()
