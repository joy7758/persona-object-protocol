# POP Adapter Model

## Purpose

POP adapters are bindings between canonical POP persona objects and
runtime-specific agent abstractions. Their role is to make persona
objects usable in concrete runtime environments without turning any one
runtime into the definition of the protocol itself.

## Design Principles

- framework neutrality
- minimal binding surface
- persona, tool, and memory separation
- runtime portability

## Adapter Responsibilities

- load a POP persona object
- validate it against the applicable schema
- map persona fields to runtime-specific constructs
- preserve unmapped fields where possible
- avoid mixing persona core with runtime-only execution metadata

## Runtime Mapping Examples

### LangChain

In LangChain, a POP adapter may bind persona fields through middleware,
prompt transformation, or runtime context shaping layers. The POP object
remains canonical, while the runtime-facing configuration is treated as
an adapter projection.

### CrewAI

In CrewAI, a POP adapter may project persona information into
role-oriented abstractions such as role, goal, and backstory. These
fields are treated as runtime-facing expressions derived from the POP
core rather than as replacements for the POP object.

### Microsoft Agent Framework

Microsoft Agent Framework is an exploratory adapter target. The current
interest is in understanding how a canonical persona object could be
bound to framework-native agent definitions without reinterpreting the
POP core as a framework-owned configuration format.

### LlamaIndex

In LlamaIndex, a POP adapter may serve as an agent-facing or
workflow-facing persona binding layer. The purpose is to project a
persona object into runtime configuration while keeping the canonical
persona definition external to the runtime.

## Portability Rules

- the same POP persona object should remain canonical across runtimes
- adapters may add runtime-specific wrappers but must not mutate persona
  core semantics

## Risks

- framework-specific lock-in
- overfitting to prompt fields
- conflating persona with permissions, memory, or tools

## Conclusion

POP adapters should prove interoperability, not redefine the protocol.
Their value lies in showing that one persona object can be projected into
multiple runtimes while preserving a stable core representation.
