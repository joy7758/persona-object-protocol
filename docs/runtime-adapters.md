# POP Runtime Adapter Layer

## Purpose

POP adapters are runtime-facing bindings for canonical persona objects.
Their purpose is to project a validated persona object into a
runtime-oriented representation without redefining the underlying POP
object.

## Current Status

- LangChain adapter scaffold
- CrewAI adapter scaffold
- both are early preview and intentionally dependency-light
- LangChain is the primary execution-layer focus in the current release line
- CrewAI remains secondary and compatibility-focused
- v0.1.5 continues to treat CrewAI as secondary while stabilizing the
  LangChain execution contract surface

## Design Principle

The canonical persona object remains primary. Adapters are projection
and binding layers built around that object, and they should preserve
its semantics rather than reshape the core schema around runtime
preferences.

## Non-Goals

- not a full runtime integration
- not official LangChain or CrewAI support
- not a guarantee of behavior equivalence across runtimes

## Future Direction

Real runtime package integrations may be added later. For the current
stage, adapter contract tests are the main proof surface: they show
that runtime-facing bindings can exist without changing the canonical
POP persona boundary.

CrewAI runtime compatibility should currently be validated on Python
3.10-3.13. Runtime-facing inputs such as tools remain outside the POP
persona core even when adapter or execution helpers are used.
