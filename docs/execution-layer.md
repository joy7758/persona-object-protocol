# POP Execution-Layer Helpers

## Purpose

POP execution-layer helpers provide runtime-facing structures derived
from canonical persona objects. Their role is to support execution-side
binding without changing the underlying schema baseline.

## Current Status

The current execution-layer release line extends early helper surfaces
for LangChain and CrewAI. These helpers remain dependency-light by
default and are designed to work as optional integration surfaces.

`v0.1.4` shifts the execution-layer focus toward LangChain. LangChain
is the primary execution-layer target in this release line, while
CrewAI remains secondary and compatibility-focused.

`v0.1.5` shifts from expanding helper surfaces to stabilizing the
LangChain execution contract surface. In this release line,
`create_langchain_execution_bundle(...)` is the main public LangChain
entry point, while compatibility helpers remain available for backward
compatibility.

## LangChain Execution Helper Surface

- `create_langchain_create_agent_kwargs(...)`
- `create_langchain_context_bundle(...)`
- `create_langchain_middleware_bundle(...)`
- `create_langchain_execution_bundle(...)`
- `maybe_build_langchain_agent_spec(...)`

These helpers target prompt, runtime-context, middleware, and tool-facing
structures aligned with LangChain v1 `create_agent` and middleware
surfaces. They remain helper-composable scaffolds, not official
LangChain runtime objects.

Compatibility helpers from the earlier execution line are retained for
backward compatibility, but they are not the primary documentation
surface for the current release line.

## CrewAI Execution Helper Surface

- `create_crewai_agent_kwargs(...)`
- `create_crewai_execution_scaffold(...)`

These helpers target Agent-style initialization surfaces such as role,
goal, backstory, tools, and optional execution flags.

CrewAI execution surfaces remain early preview in this release line.
Runtime compatibility should currently be validated on Python 3.10-3.13,
and runtime-facing inputs such as tools remain outside the POP persona
core.

## Non-Goals

- not a new schema baseline
- not a change to the canonical top-level persona boundary
- not an official LangChain or CrewAI runtime object
- not a behavior-equivalence guarantee across runtimes

## Compatibility Position

The execution-layer release line preserves the canonical schema
baseline at `v0.1.0`. The helper surfaces are runtime-facing and
optional-dependency-friendly, but they do not alter POP core semantics.

`v0.1.4` continues that compatibility position while concentrating on
LangChain optional-dependency execution helpers. `v0.1.5` further
stabilizes that line as an execution contract surface. The canonical
schema baseline remains `v0.1.0`.
