# LangChain Execution Contract Note

## What POP currently provides

POP currently provides a persona-object-derived execution contract
surface aligned with LangChain v1 `create_agent`, middleware, and
runtime-context helper semantics.

The current primary entry point is:

- `create_langchain_execution_bundle(...)`

Supporting public helpers remain:

- `create_langchain_create_agent_kwargs(...)`
- `create_langchain_context_bundle(...)`
- `create_langchain_middleware_bundle(...)`
- `maybe_build_langchain_agent_spec(...)`

## What POP does not claim

- POP is not attempting to redefine LangChain runtime types
- POP does not claim official LangChain runtime integration
- POP does not claim behavior equivalence or live execution guarantees
- POP does not move tools into the POP persona core

## Recommended First Evaluation Path

Install:

```bash
pip install "pop-persona[langchain]"
```

Run:

```bash
python examples/integrations/langchain_minimal_20_lines.py
python examples/integrations/langchain_installed_smoke_minimal.py
```

What to look for:

- `create_agent_kwargs`
- `context_bundle`
- `middleware_bundle`
- `langchain_available` in the optional-dependency spec path

What not to assume:

- this is not an official LangChain runtime object
- this is not a live model execution path
- this is not a behavior-equivalence guarantee

## Current Contract Surface

The current contract surface is runtime-facing and helper-composable:

- `create_langchain_execution_bundle(...)` is the main public surface
- `create_langchain_create_agent_kwargs(...)` reflects
  `create_agent(...)`-aligned parameter semantics
- `create_langchain_context_bundle(...)` remains a runtime-context
  scaffold, not a claim about official `create_agent` parameters
- `create_langchain_middleware_bundle(...)` is middleware-facing
- `maybe_build_langchain_agent_spec(...)` supports dependency-aware
  first-evaluation paths

## Compatibility Notes

Compatibility helpers remain available for backward compatibility, but
they are not the recommended first-adoption path.

The canonical schema baseline remains `v0.1.0`.

## Why schema baseline remains stable while package releases advance

POP package releases can advance independently from the canonical
schema baseline. The current package surface has continued to evolve
while the canonical schema baseline remains `v0.1.0`, which keeps the
structural persona boundary stable during runtime-facing experimentation.
