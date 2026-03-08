# Persona Object Protocol (POP)

[![CI](https://github.com/joy7758/persona-object-protocol/actions/workflows/validate.yml/badge.svg)](https://github.com/joy7758/persona-object-protocol/actions/workflows/validate.yml)
[![PyPI](https://img.shields.io/pypi/v/persona-object-protocol)](https://pypi.org/project/persona-object-protocol/)
[![Python](https://img.shields.io/pypi/pyversions/persona-object-protocol)](https://pypi.org/project/persona-object-protocol/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18907957.svg)](https://doi.org/10.5281/zenodo.18907957)
[![Release](https://img.shields.io/github/v/release/joy7758/persona-object-protocol)](https://github.com/joy7758/persona-object-protocol/releases)
[![License](https://img.shields.io/github/license/joy7758/persona-object-protocol)](./LICENSE)

## A lightweight draft protocol for portable persona objects in multimodal AI systems

POP is a lightweight public draft for representing portable persona objects with explicit boundaries. POP is a framework-neutral persona object protocol for agent runtimes. It is positioning-first and protocol-oriented: not a product, not a persona generation pipeline, and not a full runtime stack.

Preferred scholarly citation for POP is the POP-Core paper: [10.5281/zenodo.18907957](https://doi.org/10.5281/zenodo.18907957).

The repository itself is separately archived on Zenodo at [10.5281/zenodo.18898252](https://doi.org/10.5281/zenodo.18898252) for version-specific software citation.

For minimal citation guidance, see [`docs/cite-pop.md`](docs/cite-pop.md).

## Digital Biosphere Ecosystem

This repository is part of the **Digital Biosphere Architecture**.

Architecture overview:
[digital-biosphere-architecture](https://github.com/joy7758/digital-biosphere-architecture)

## Positioning

- POP is not a full agent framework.
- POP is not a prompt template library.
- POP is not a memory or permissions system.
- POP focuses on portable persona objects and adapter-based runtime projection.

## Ecosystem Direction

- LangChain integration
- CrewAI projection
- Microsoft Agent Framework exploration
- LlamaIndex exploration

For the current ecosystem plan, see [`docs/pop-ecosystem-roadmap.md`](docs/pop-ecosystem-roadmap.md).
For the adapter strategy, see [`docs/pop-adapter-model.md`](docs/pop-adapter-model.md).

## Portability Demo

An early cross-runtime portability scaffold is available at
[`examples/cross-runtime-persona-portability/README.md`](examples/cross-runtime-persona-portability/README.md).

## Python SDK (Early Preview)

A minimal Python SDK is provided as an early preview for loading,
validating, and projecting canonical POP persona objects.

Install from the repository root:

```bash
pip install -e .
```

CLI example:

```bash
pop-inspect examples/cross-runtime-persona-portability/personas/lawyer_persona.json
```

Python API example:

```python
from pop import load_persona, validate_persona
from pop.projections import project_to_crewai, project_to_langchain

persona = load_persona(
    "examples/cross-runtime-persona-portability/personas/lawyer_persona.json"
)
validate_persona(persona)

langchain_view = project_to_langchain(persona)
crewai_view = project_to_crewai(persona)
```

## POP-Core Paper

Zhang, B. (2026). *POP-Core: Formal Semantics and Interoperability of Portable Persona Objects*. Zenodo. https://doi.org/10.5281/zenodo.18907957

## What POP is

POP defines a minimal object layer for packaging persona definitions in a portable and inspectable form. It focuses on persona object representation, plugin attachment entry points, separation from memory and permissions, and basic governance boundaries.

## What POP solves

POP provides a minimal shared structure for describing persona objects across systems. Its purpose is to keep persona definitions distinct from memory stores, capability grants, and application-specific orchestration logic.

## Scope

POP v0.1 covers:

- a minimal persona core
- optional memory hook declarations
- optional plugin manifest declarations
- explicit safety and governance boundaries
- simple draft version labeling

## Non-goals

POP is not:

- a full personality generation system
- a model training or fine-tuning method
- a robotics stack
- a digital immortality framework
- a universal cross-model persona injection method
- a substitute for permission, identity, or memory systems

## Minimal structure

A POP object is intentionally small. The reference structure in this repository includes:

- `schema_version` for draft compatibility
- `id`, `name`, and `description` for identity and positioning
- `traits`, `anchors`, and `behavior` for the persona core
- `memory_hooks` as references to separate memory subsystems
- `plugins` as declarative attachment entry points

The object does not embed long-term memory, permission grants, or execution policy.

## Relationship to adjacent work

POP complements adjacent work on persona steering, persona consistency, agent tooling, and agent security. It does not replace those areas. Its role is narrower: to define a portable persona object layer that other systems can interpret, constrain, or extend.

For external messaging and positioning copy, see [`docs/communication-kit.md`](docs/communication-kit.md).

## Repository structure

```text
.
├── .zenodo.json
├── CITATION.cff
├── LICENSE
├── README.md
├── adapters
│   ├── crewai
│   ├── langchain
│   ├── llamaindex
│   └── microsoft-agent-framework
├── docs
│   ├── README.md
│   ├── cite-pop.md
│   ├── communication-kit.md
│   ├── pop-adapter-model.md
│   ├── pop-ecosystem-roadmap.md
│   └── short-outreach-kit.md
├── examples
│   ├── cross-runtime-persona-portability
│   ├── caregiver.persona.json
│   ├── companion.persona.json
│   └── mentor.persona.json
├── schema
│   └── persona.schema.json
└── spec
    └── pop-0.1.md
```

## Status

This repository contains a positioning-first `v0.1.0-draft`. It is a draft protocol, not a stable standard, and not a guarantee of high-fidelity persona transfer across models or products.

For a forward-looking RFC-style core draft, see [`spec/POP-core.md`](spec/POP-core.md).
For the draft canonical JSON binding, see [`spec/POP-json-binding.md`](spec/POP-json-binding.md) and [`schema/pop.schema.json`](schema/pop.schema.json).
For minimal runtime integration patterns, see [`docs/interop.md`](docs/interop.md).

## CLI

The repository now includes a minimal reference CLI for POP:

```bash
python3 -m pip install -e .
pop validate examples/mentor.v1.json
pop project examples/mentor.v1.json --runtime prompt
pop migrate-pop01 examples/mentor.persona.json
```

For direct local execution without installation:

```bash
python3 cli/pop_cli.py validate examples/mentor.v1.json
```

## LangChain Integration

POP now includes a first runtime integration for LangChain:

```bash
python3 -m pip install -e ".[langchain]"
python3 examples/langchain_agent.py examples/mentor.v1.json --print-config
```

Middleware-oriented preview package:

```bash
python3 examples/langchain_middleware_demo.py --print-config
```

The installed package exposes `langchain_pop` as a middleware-oriented preview layer for LangChain agents. It injects the POP-derived system prompt, preserves persona identity in runtime state, and filters tools against POP boundaries.

An extraction-ready standalone package scaffold is available at [`integrations/langchain-pop`](integrations/langchain-pop).

If you have `OPENAI_API_KEY` configured, you can invoke a live LangChain agent:

```bash
python3 examples/langchain_agent.py examples/mentor.v1.json --model gpt-4.1-mini
python3 examples/langchain_middleware_demo.py --invoke --model gpt-4.1-mini
```

Package API:

```python
from pop_protocol.adapters.langchain import create_langchain_agent, pop_to_langchain_config
from langchain_pop.agent import create_pop_agent
from langchain_pop.middleware import POPMiddleware
```

## CI And Packaging

The repository includes a GitHub Actions workflow at [`.github/workflows/validate.yml`](.github/workflows/validate.yml) that:

- validates all JSON example objects with `pop validate`
- builds the Python distribution with `python -m build`

Typical local packaging commands:

```bash
python3 -m pip install -e .
python3 -m pip install build
python3 -m build
```

The repository also includes a release workflow at [`.github/workflows/publish.yml`](.github/workflows/publish.yml). Pushing a tag such as `v0.1.0` will build the package and publish it to PyPI through GitHub Actions.
