[![CI](https://github.com/joy7758/langchain-pop/actions/workflows/test.yml/badge.svg)](https://github.com/joy7758/langchain-pop/actions/workflows/test.yml)
[![PyPI version](https://img.shields.io/pypi/v/langchain-pop.svg)](https://pypi.org/project/langchain-pop/)
[![Python versions](https://img.shields.io/pypi/pyversions/langchain-pop.svg)](https://pypi.org/project/langchain-pop/)
[![License](https://img.shields.io/pypi/l/langchain-pop.svg)](https://pypi.org/project/langchain-pop/)

# langchain-pop

`langchain-pop` is a preview middleware package that brings portable persona objects into LangChain agent runtimes.

It allows POP persona objects to be loaded into LangChain, injected as runtime persona framing, and enforced through boundary-aware tool filtering. The package is designed as a middleware and toolkit-style ecosystem integration for the Persona Object Protocol (POP), not as a replacement for LangChain's own agent abstractions.

## Status

`langchain-pop` is an early integration preview.

Current capabilities include:

- POP v1 canonical object loading
- legacy `pop-0.1` migration
- persona-aware system prompt construction
- boundary-based tool filtering
- LangChain agent construction via `create_pop_agent(...)`

This package currently demonstrates runtime integration and middleware behavior. It does not yet provide a full interoperability benchmark or production-grade governance system.

## Installation

### Minimal install

```bash
pip install langchain-pop
```

### With OpenAI provider support

```bash
pip install "langchain-pop[openai]"
```

## Quick Start

```python
from langchain_openai import ChatOpenAI

from langchain_pop.agent import create_pop_agent


def knowledge_lookup(topic: str) -> str:
    """Look up a topic in a mock knowledge base."""
    return f"Knowledge lookup result for: {topic}"


agent = create_pop_agent(
    pop_source="tests/fixtures/mentor.v1.json",
    model=ChatOpenAI(model="gpt-4o", temperature=0.0),
    tools=[knowledge_lookup],
    name="mentor_agent",
)

print(agent)
```

To inspect the generated runtime configuration without invoking a live model:

```bash
python examples/langchain_middleware_demo.py --print-config
```

## What langchain-pop does

`langchain-pop` maps a POP persona object into LangChain runtime components:

- persona role and traits -> system-level runtime framing
- persona boundaries -> runtime tool filtering
- POP identity fields -> runtime persona state

This makes persona handling more structured than ad hoc prompt-only role injection and aligns the integration with a toolkit-style runtime workflow instead of a thin adapter layer.

## Example: Middleware Preview

```python
from langchain_pop.middleware import POPMiddleware

middleware = POPMiddleware("tests/fixtures/mentor.v1.json")

print(middleware.persona_state())
print(middleware.system_prompt)
```

## Example: Legacy Migration

Legacy `pop-0.1` objects are supported through automatic migration:

```python
from langchain_pop.agent import create_pop_agent
from langchain_openai import ChatOpenAI


agent = create_pop_agent(
    pop_source="tests/fixtures/mentor.pop01.json",
    model=ChatOpenAI(model="gpt-4o", temperature=0.0),
    tools=[],
)
```

## Design Scope

`langchain-pop` is designed as a LangChain ecosystem integration for portable persona objects.

It is not:

- a full agent framework
- a replacement for LangChain middleware
- a production governance framework
- a complete interoperability standard

Its purpose is to demonstrate that POP persona objects can function as runtime-integrated persona middleware in a real agent stack.

## Docs PR Draft

The repository includes a docs-PR-oriented draft page in two forms:

- [`docs/langchain_pop.mdx`](docs/langchain_pop.mdx): toolkit-oriented draft matching the LangChain docs naming style
- [`docs/langchain-docs-pr-draft.md`](docs/langchain-docs-pr-draft.md): local draft copy for iterative editing

## Repository Structure

```text
langchain-pop/
├── src/langchain_pop/
│   ├── __init__.py
│   ├── _pop_compat.py
│   ├── middleware.py
│   └── agent.py
├── tests/
├── examples/
├── docs/
└── README.md
```

## Development

Run tests:

```bash
python -m unittest discover -s tests -v
```

Build distributions:

```bash
python -m build
```

Run demo:

```bash
python examples/langchain_middleware_demo.py --print-config
```

For local editable development:

```bash
pip install -e .
```

## Relationship to POP

`langchain-pop` is an ecosystem integration layer for portable persona objects.

- `persona-object-protocol` defines the protocol semantics, schema, examples, and reference tooling.
- `langchain-pop` demonstrates how POP persona objects can be consumed inside a real agent runtime.

In other words:

- POP = protocol layer
- `langchain-pop` = runtime integration layer

## Maturity

This package should currently be understood as:

- an early middleware preview
- a runtime integration proof point
- a bridge between POP and LangChain agents

It should not yet be interpreted as a final or official LangChain standard component.
