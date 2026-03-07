# Persona Object Protocol (POP)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18898252.svg)](https://doi.org/10.5281/zenodo.18898252)
[![Release](https://img.shields.io/github/v/release/joy7758/persona-object-protocol)](https://github.com/joy7758/persona-object-protocol/releases)
[![License](https://img.shields.io/github/license/joy7758/persona-object-protocol)](./LICENSE)

## A lightweight draft protocol for portable persona objects in multimodal AI systems

POP is a lightweight public draft for representing portable persona objects with explicit boundaries. It is positioning-first and protocol-oriented: not a product, not a persona generation pipeline, and not a full runtime stack.

POP is publicly archived on Zenodo and can be cited via DOI: [10.5281/zenodo.18898252](https://doi.org/10.5281/zenodo.18898252).

For minimal citation guidance, see [`docs/cite-pop.md`](docs/cite-pop.md).

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
├── docs
│   ├── cite-pop.md
│   ├── communication-kit.md
│   └── short-outreach-kit.md
├── examples
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
