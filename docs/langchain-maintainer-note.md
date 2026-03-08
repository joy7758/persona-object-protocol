# LangChain Execution Contract Note

## Purpose

This note provides a minimal maintainer-facing summary of how POP
currently approaches LangChain integration.

## Current Claim

POP does not claim an official LangChain integration. The current
release line provides an early execution contract surface aligned with
LangChain v1 `create_agent`, middleware, and runtime-context helper
semantics.

The main public entry point in this release line is
`create_langchain_execution_bundle(...)`.

## What the Current Contract Surface Provides

- `create_langchain_execution_bundle(...)` as the primary LangChain
  execution contract surface
- `create_langchain_create_agent_kwargs(...)` for
  `create_agent(...)`-aligned parameter semantics
- `create_langchain_context_bundle(...)` as a helper-composable
  runtime-context scaffold
- `create_langchain_middleware_bundle(...)` as a middleware-facing
  helper bundle
- `maybe_build_langchain_agent_spec(...)` as a dependency-aware helper
  spec path when the optional `langchain` extra is installed

These surfaces return runtime-facing helper structures. They do not
construct live agent runs, do not require model calls, and do not
present themselves as official LangChain runtime objects.

## Boundary Conditions

- POP remains a persona object protocol, not a full runtime framework
- the canonical schema baseline remains `v0.1.0`
- tools remain runtime-facing inputs and are not written into the POP
  persona core
- compatibility helpers remain available for backward compatibility but
  are no longer the primary documented path

## Minimal Install Path

```bash
pip install "pop-persona[langchain]"
```

## Minimal Example Path

- `examples/integrations/langchain_create_agent_minimal.py`
- `examples/integrations/langchain_execution_minimal.py`
- `examples/integrations/langchain_installed_contract_minimal.py`

## Reviewer Shortcut

If one sentence is needed, the current position is:

POP stabilizes a LangChain-facing execution contract surface around
`create_langchain_execution_bundle(...)` without changing the canonical
schema baseline or claiming official LangChain runtime integration.
