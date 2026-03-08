# langchain-pop

Portable persona middleware for LangChain agents.

This page is a draft for a future LangChain docs repo integration page. It assumes `langchain-pop` is published as a standalone package and `persona-object-protocol` is available as the canonical POP parser and schema layer.

## Installation

```bash
python -m pip install persona-object-protocol
python -m pip install "langchain-pop[openai]"
```

## Why langchain-pop

`langchain-pop` connects Persona Object Protocol (POP) objects to LangChain's native agent runtime. It is designed as middleware rather than a prompt-only adapter.

The integration provides:

- POP-derived system prompt injection
- persona identity retention in runtime state
- boundary-aware tool filtering
- legacy POP 0.1 migration support through the POP core package

## Quick Start

```python
from langchain_openai import ChatOpenAI

from langchain_pop.agent import create_pop_agent


def knowledge_lookup(topic: str) -> str:
    """Look up a topic in a mock knowledge base."""
    return f"Knowledge lookup result for: {topic}"


pop_object = {
    "kind": "persona-object",
    "id": "persona:mentor:docs",
    "version": "1.0.0",
    "role": "mentor",
    "traits": ["calm", "analytical", "structured"],
    "boundaries": {
        "financial_advice": False
    },
    "status": "active",
    "provenance": {
        "issuer": "langchain-pop-docs",
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

## Using POPMiddleware Directly

```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from langchain_pop.middleware import POPMiddleware


middleware = POPMiddleware("mentor.v1.json")
model = ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)

agent = create_agent(
    model=model,
    tools=[knowledge_lookup],
    middleware=[middleware],
    name="mentor_agent",
)
```

## Boundary-Aware Tool Filtering

If a POP boundary targets a tool, `POPMiddleware` removes that tool from the available tool list before the model call. If a blocked tool call still appears at runtime, the middleware returns an explicit error `ToolMessage`.

Example boundary:

```json
{
  "tool.salary_estimator": {
    "decision": "disallow",
    "reason": "Salary estimation is outside this mentor persona's approved scope."
  }
}
```

With that boundary active:

- `knowledge_lookup` remains available
- `salary_estimator` is filtered out before the model call
- direct runtime use of `salary_estimator` is blocked with a POP boundary error

## Legacy POP 0.1 Migration

`langchain-pop` accepts legacy POP 0.1 objects through the `persona-object-protocol` dependency. The POP core package migrates the legacy object to the canonical POP v1 structure before the middleware uses it.

```python
from langchain_pop.middleware import POPMiddleware

middleware = POPMiddleware("mentor.pop01.json")
print(middleware.persona_state()["version"])
# 1.0.0-migrated
```

## Relationship to persona-object-protocol

`persona-object-protocol` remains the protocol mother package:

- POP core semantics
- POP JSON binding
- schema validation
- CLI

`langchain-pop` is the runtime integration package:

- LangChain middleware
- LangChain agent constructor helper
- runtime-facing examples and tests

## Development Notes

Recommended minimum checks before submitting a docs PR:

```bash
python -m unittest discover -s tests
python examples/langchain_middleware_demo.py --print-config
```
