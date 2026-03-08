# Cross-Runtime Persona Portability Demo

## Objective

This example is intended to show how the same POP persona object can be
mapped to multiple agent runtimes. The emphasis is on portability of the
persona core rather than on identical runtime behavior.

## Canonical Persona Object

The canonical source for this demo is a POP persona object JSON file:
[`personas/lawyer_persona.json`](personas/lawyer_persona.json).

## Runtime Targets

- [LangChain](langchain/README.md)
- [CrewAI](crewai/README.md)

## Mapping Strategy

- LangChain: binding through middleware, prompt shaping, or runtime
  context projection
- CrewAI: binding through role, goal, and backstory style projection

## What This Demo Proves

- persona portability
- separation of persona core from runtime-specific configuration
- cross-runtime reproducibility of persona intent

## What This Demo Does Not Prove

- identical runtime behavior is not guaranteed
- POP does not replace the runtime
- adapters are interpretive bindings, not behavioral proofs
