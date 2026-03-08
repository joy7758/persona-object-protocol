# POP Execution-Layer Helpers

## Purpose

POP execution-layer helpers provide runtime-facing structures derived
from canonical persona objects. Their role is to support execution-side
binding without changing the underlying schema baseline.

## Current Status

`v0.1.3` planning focuses on early execution-layer helpers for
LangChain and CrewAI. These helpers remain dependency-light by default
and are designed to work as optional integration surfaces.

## LangChain Execution Helper Surface

- `create_langchain_agent_kwargs(...)`
- `create_langchain_execution_scaffold(...)`
- `create_langchain_middleware_scaffold(...)`

These helpers target prompt, context, middleware, and tool-facing
structures that can be consumed by LangChain-side execution entry
points.

## CrewAI Execution Helper Surface

- `create_crewai_agent_kwargs(...)`
- `create_crewai_execution_scaffold(...)`

These helpers target Agent-style initialization surfaces such as role,
goal, backstory, tools, and optional execution flags.

## Non-Goals

- not a new schema baseline
- not a change to the canonical top-level persona boundary
- not an official LangChain or CrewAI runtime object
- not a behavior-equivalence guarantee across runtimes

## Compatibility Position

`v0.1.3` focuses on execution-layer helpers while preserving the
canonical schema baseline at `v0.1.0`. The helper surfaces are
runtime-facing and optional-dependency-friendly, but they do not alter
POP core semantics.
