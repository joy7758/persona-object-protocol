---
title: langchain-pop
subtitle: Portable persona middleware for LangChain agents
---

# langchain-pop

`langchain-pop` is a middleware-style integration package for using POP persona objects inside LangChain agents.

It allows portable persona objects to be loaded, migrated from legacy POP drafts, converted into runtime persona framing, and enforced through boundary-aware tool filtering.

## Why use langchain-pop

Many persona configurations in agent systems are still represented as prompt fragments or local configuration blocks. `langchain-pop` provides a more structured path by treating persona as a portable object that can be loaded into runtime state and reflected in agent behavior.

This package is useful when you want:

- structured persona loading instead of ad hoc prompt-only role injection
- portable persona objects across agent runtimes
- runtime persona state with explicit identity fields
- boundary-aware tool filtering

## Installation

```bash
pip install langchain-pop
```

Or for local development:

```bash
pip install -e ".[openai]"
```

## Quickstart

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

## Inspect middleware output

To inspect runtime persona configuration without invoking a live model:

```bash
python examples/langchain_middleware_demo.py --print-config
```

This prints:

- persona state
- generated system prompt
- allowed tools
- blocked tools

## POP Middleware

`POPMiddleware` is the central integration point.

It is responsible for:

- loading canonical POP persona objects
- migrating legacy `pop-0.1` objects
- constructing runtime persona framing
- filtering tools according to persona boundaries

Example:

```python
from langchain_pop.middleware import POPMiddleware

middleware = POPMiddleware("tests/fixtures/mentor.v1.json")

print(middleware.persona_state())
print(middleware.system_prompt)
```

## Boundary-aware tool filtering

`langchain-pop` can block or filter tools based on persona boundary rules.

For example, if a persona object disallows finance-related actions, a tool such as `salary_estimator` can be filtered out before runtime use.

This allows persona constraints to influence runtime tool availability rather than existing only as prompt instructions.

## Legacy migration

Legacy `pop-0.1` inputs are supported through automatic migration.

```python
from langchain_openai import ChatOpenAI

from langchain_pop.agent import create_pop_agent


agent = create_pop_agent(
    pop_source="tests/fixtures/mentor.pop01.json",
    model=ChatOpenAI(model="gpt-4o", temperature=0.0),
    tools=[],
)
```

## What this integration is

`langchain-pop` is:

- a LangChain ecosystem integration
- a persona middleware preview
- a runtime bridge for POP persona objects

## What this integration is not

`langchain-pop` is not:

- a replacement for LangChain agents
- a complete governance framework
- a full interoperability benchmark
- an official LangChain core primitive

## Project status

This package is currently an early integration preview.

It demonstrates that POP persona objects can be consumed by a real agent runtime and converted into middleware-governed persona behavior. It should be understood as an ecosystem integration package rather than a final standard component.
