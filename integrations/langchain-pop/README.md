# langchain-pop

Portable persona middleware for LangChain agents.

`langchain-pop` is the extraction-ready runtime integration package for Persona Object Protocol (POP). It keeps the POP protocol layer in `persona-object-protocol` and exposes a LangChain-native middleware/toolkit layer for agent construction.

The package centers on two entry points:

- `POPMiddleware`: injects a POP-derived system prompt, preserves persona identity in agent state, and filters tools against POP boundaries
- `create_pop_agent(...)`: convenience wrapper that attaches `POPMiddleware` to `langchain.agents.create_agent(...)`

## Install

Published path:

```bash
python -m pip install persona-object-protocol
python -m pip install "langchain-pop[openai]"
```

Local development from this monorepo:

```bash
python -m pip install -e ../../
python -m pip install -e ".[openai]"
```

## Quick Start

```python
from langchain_openai import ChatOpenAI

from langchain_pop.agent import create_pop_agent


def knowledge_lookup(topic: str) -> str:
    """Look up a topic in a mock knowledge base."""
    return f"Knowledge lookup result for: {topic}"


pop_object = {
    "kind": "persona-object",
    "id": "persona:mentor:quickstart",
    "version": "1.0.0",
    "role": "mentor",
    "traits": ["calm", "analytical", "structured"],
    "boundaries": {
        "tool.knowledge_lookup": {
            "decision": "allow",
            "reason": "Knowledge lookup is within scope."
        },
        "financial_advice": False
    },
    "status": "active",
    "provenance": {
        "issuer": "langchain-pop-readme",
        "created": "2026-03-08"
    }
}

model = ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)
agent = create_pop_agent(
    pop_source=pop_object,
    model=model,
    tools=[knowledge_lookup],
    name="mentor_agent",
)
```

## Boundary-Aware Tool Filtering

```python
from langchain_pop.middleware import POPMiddleware


def knowledge_lookup(topic: str) -> str:
    """Look up a topic in a mock knowledge base."""
    return topic


def salary_estimator(role: str) -> str:
    """Estimate salary bands for a role."""
    return role


middleware = POPMiddleware("tests/fixtures/mentor.v1.json")
allowed_tools, blocked_tools = middleware.filter_tools(
    [knowledge_lookup, salary_estimator]
)
```

For the `mentor.v1.json` fixture, `knowledge_lookup` remains available and `salary_estimator` is blocked by the `tool.salary_estimator` boundary.

## Legacy POP 0.1 Support

Legacy POP 0.1 objects are accepted as migration inputs. `POPMiddleware` loads a legacy object, migrates it to the canonical POP v1 shape, and then proceeds with normal middleware behavior.

```python
from langchain_pop.middleware import POPMiddleware

middleware = POPMiddleware("tests/fixtures/mentor.pop01.json")
print(middleware.persona_state()["version"])
# 1.0.0-migrated
```

## Demo

```bash
python examples/langchain_middleware_demo.py --print-config
python examples/langchain_middleware_demo.py --invoke --model gpt-4.1-mini
```

## Tests

```bash
python -m unittest discover -s tests
```

## Repository Layout

```text
langchain-pop/
  pyproject.toml
  README.md
  docs/
    langchain-docs-pr-draft.md
  examples/
    langchain_middleware_demo.py
  src/
    langchain_pop/
      __init__.py
      agent.py
      middleware.py
  tests/
    fixtures/
    test_agent.py
    test_middleware.py
```
