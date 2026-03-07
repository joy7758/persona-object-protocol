# Persona Object Protocol (POP)

## A lightweight draft protocol for portable persona objects in future multimodal AI systems

POP is a compact draft protocol for representing portable persona objects across future multimodal AI systems. It is intended as a protocol-carding repository: small enough to discuss, inspect, and adapt, without presenting itself as a product, a generation pipeline, or a full runtime stack.

## What POP is

POP is a lightweight draft protocol for packaging a persona definition into a portable object with explicit boundaries. In conservative terms, it aims to provide a multimodal persona object layer, and potentially a persona sovereignty layer, for systems that need persona portability without collapsing persona, memory, permissions, and tooling into one artifact.

POP focuses on:

- persona object representation
- plugin attachment entry points
- separation from memory and permissions
- basic governance boundaries

## What POP solves

POP gives implementers a minimal shared structure for describing a persona object in a way that can move between systems. It helps keep persona definition separate from memory stores, capability grants, and application-specific orchestration logic.

## Scope

POP v0.1 covers:

- a minimal persona core
- optional memory hook declarations
- optional plugin manifest declarations
- explicit safety and governance boundaries
- simple version labeling for draft interoperability

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

## Repository structure

```text
.
├── .zenodo.json
├── CITATION.cff
├── LICENSE
├── README.md
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
