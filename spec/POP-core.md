# POP v1.0 Core Draft

Draft Specification

Status: Work in progress. This document defines a forward-looking core specification for POP v1.0. It does not retroactively change the existing `pop-0.1` draft artifacts in this repository.

Archived paper reference: Zhang, B. (2026). *POP-Core: Formal Semantics and Interoperability of Portable Persona Objects*. Zenodo. `https://doi.org/10.5281/zenodo.18907957`

## 1. Introduction

Persona Object Protocol (POP) defines a portable persona object layer for AI agents.

The goal of POP is to represent persona-bearing objects as structured, portable, and verifiable artifacts that can be interpreted across different AI runtimes.

Many current AI systems rely on:

- system prompts
- ad hoc configuration
- runtime-specific agent definitions

These approaches often lack:

- portability
- lifecycle control
- auditability

POP introduces a standardized persona object abstraction intended to keep persona definition separate from runtime policy, memory state, and tool execution logic.

## 2. Scope and Non-Goals

This draft specifies:

- a minimal persona object abstraction
- lifecycle operations over persona objects
- runtime projection semantics
- preservation reporting concepts
- conformance levels

This draft does not specify:

- model training or fine-tuning methods
- a universal prompt format
- tool invocation protocols
- memory retrieval protocols
- permission or identity systems

## 3. Conventions

The key words "MUST", "MUST NOT", "SHOULD", "SHOULD NOT", and "MAY" in this document are to be interpreted as described in RFC 2119.

## 4. Architectural Position

In an AI agent stack, POP occupies the persona object layer:

```text
User
  |
  v
Agent Runtime
  |
  v
Persona Object Layer (POP)
  |
  v
Memory Layer
  |
  v
Tool Layer
  |
  v
External Systems
```

POP addresses persona object portability. It is adjacent to, but distinct from, other protocol layers:

| Layer | Example Focus |
| --- | --- |
| Tool integration | MCP-style tool and context integration |
| Agent communication | A2A-style agent-to-agent exchange |
| Agent configuration | runtime- or vendor-specific agent specs |
| Persona portability | POP |

An implementation MAY combine POP with these protocols, but POP does not replace them.

## 5. Terminology

### 5.1 Persona Object

A structured representation of a persona used by an AI system.

A Persona Object MUST be interpretable as an object artifact rather than as a human identity, permission grant, or runtime instance.

### 5.2 Runtime

A software environment that consumes persona objects.

Examples include:

- prompt runtimes
- application runtimes
- agent runtimes

### 5.3 Projection

A transformation of a POP object into a runtime-specific representation.

Projection MAY preserve, weaken, or lose parts of the original persona object.

### 5.4 Boundary

A declared limit on behavior, authority, or identity claims associated with a persona object.

Boundaries MUST NOT be interpreted as capability grants.

### 5.5 Provenance

Metadata describing the origin, authorship, or issuance context of a persona object.

## 6. Design Principles

POP implementations SHOULD preserve the following principles:

- separation of persona objects from memory contents
- separation of persona objects from permission grants
- separation of persona objects from runtime orchestration logic
- explicit treatment of boundaries as constraints rather than authority
- conservative portability across runtimes

## 7. POP Object Model

At the semantic level, a POP object is defined as:

```text
P = <id, role, traits, boundaries, status, provenance, version>
```

Where:

| Field | Description | Core Expectation |
| --- | --- | --- |
| `id` | unique identifier | MUST distinguish the object within implementation scope |
| `role` | persona role | MUST express the primary role framing |
| `traits` | behavioral characteristics | SHOULD capture durable descriptive tendencies |
| `boundaries` | authority or behavior constraints | MUST express limits, not grants |
| `status` | lifecycle state | SHOULD indicate whether the object is active, replaced, revoked, or otherwise non-current |
| `provenance` | origin metadata | SHOULD support audit and origin inspection |
| `version` | object version | MUST change when semantics materially change |

Companion schemas MAY define additional fields such as descriptive summaries, anchor statements, interaction style, memory hooks, or plugin manifests.

## 8. Serialization Requirements

A serialized POP object MUST:

- be machine-readable
- be versioned
- preserve explicit boundary information
- remain distinguishable from runtime state

A serialized POP object SHOULD:

- be JSON or another inspectable structured representation
- include provenance metadata
- support deterministic validation

Implementations MUST NOT embed live runtime state, permission grants, or mutable memory contents as part of the core persona object.

## 9. Example Object

```json
{
  "id": "persona:mentor:v1",
  "version": "1.0",
  "role": "mentor",
  "traits": ["calm", "analytical"],
  "boundaries": {
    "financial_advice": false
  },
  "status": "active",
  "provenance": {
    "author": "example",
    "created": "2026-03-01"
  }
}
```

This example is illustrative. Concrete POP schema bindings MAY define a richer structure.

## 10. Lifecycle Operations

POP defines five core lifecycle operations.

### 10.1 `attach(P)`

Activate a persona object in a runtime context.

```text
Sigma -> Sigma[P active]
```

An implementation performing `attach(P)` MUST bind the object into runtime context without treating the object itself as a permission grant.

### 10.2 `detach(P)`

Deactivate an attached persona object.

```text
Sigma -> Sigma[P null]
```

An implementation performing `detach(P)` SHOULD ensure that further persona-specific behavior is no longer derived from `P`.

### 10.3 `project(P, delta)`

Transform a persona object into a runtime-specific representation.

```text
P -> pi_delta
```

Where `delta` denotes the target runtime.

An implementation performing projection MUST NOT silently convert omitted boundaries into implied permissions.

### 10.4 `replace(P_old, P_new)`

Replace an existing persona object with an updated version.

An implementation performing `replace` SHOULD preserve an audit link between the previous and replacement object.

### 10.5 `revoke(P)`

Mark a persona object as invalid for future use.

An implementation supporting revocation MUST prevent ordinary attachment of revoked objects unless an explicit override policy exists outside the POP object itself.

## 11. Runtime Projection

Runtime projection MAY result in partial information preservation.

POP defines three preservation states:

| State | Meaning |
| --- | --- |
| `complete` | field preserved exactly |
| `weakened` | field partially preserved |
| `lost` | field removed or no longer recoverable |

Prompt-based runtimes are likely to weaken structure by flattening fields into text. Structured runtimes MAY preserve more information by maintaining explicit persona slots.

## 12. Preservation Function

For a runtime `delta` and field `f`, POP defines:

```text
preserve_delta(P, f) in {complete, weakened, lost}
```

This function characterizes the preservation status of a field after projection into runtime `delta`.

Implementations SHOULD report preservation at least for identity, role, boundaries, and version information when feasible.

## 13. Conformance Levels

POP defines three conformance levels.

### 13.1 POP-Core

Minimum requirements:

- schema validation
- lifecycle operations
- runtime projection

### 13.2 POP-Interop

Additional requirements:

- identity preservation reporting
- round-trip transformation support or documented loss model
- per-field preservation reporting

### 13.3 POP-Governance

Advanced features:

- provenance verification
- lifecycle audit support
- revocation support

## 14. Security Considerations

Persona objects introduce several security risks.

### 14.1 Authority Escalation

A runtime may allow actions outside declared persona boundaries.

### 14.2 Prompt Injection

Prompt-based runtimes may override or dilute persona constraints.

### 14.3 Boundary Violation

Memory or tool outputs may redefine persona attributes or implied authority.

### 14.4 Identity Overloading

An implementation may incorrectly treat a persona object as identity proof, account ownership, or legal authority.

POP implementations SHOULD enforce boundary constraints during runtime projection and MUST keep identity, permission, audit, and policy systems outside the persona object unless explicitly defined by a separate protocol.

## 15. Interoperability Evaluation

POP implementations SHOULD support evaluation metrics.

### 15.1 Field Preservation Ratio

```text
FPR = (complete + 0.5 * weakened) / fields
```

### 15.2 Identity Retention

Implementations SHOULD check preservation of at least:

```text
id
version
status
```

### 15.3 Round-Trip Loss

```text
POP -> runtime -> POP'
```

Implementations SHOULD measure the difference between `P` and `P'` and document unrecoverable loss.

## 16. Conformance Checklist

Implementations claiming POP support MUST:

- validate POP schema
- support `attach`
- support `detach`
- support runtime projection

Implementations claiming POP-Interop SHOULD:

- report preservation metrics
- support round-trip transformation or publish a documented loss profile

Implementations claiming POP-Governance SHOULD:

- support provenance inspection
- support lifecycle audit
- support revocation handling

## 17. Future Work

Future extensions may include:

- cryptographic provenance
- governance integration
- cross-runtime persona negotiation
- canonical JSON bindings and companion schemas
- reference validators and interoperability test suites

## 18. Conclusion

POP introduces a minimal persona object layer for AI agents.

By separating persona objects from runtime configuration, POP aims to enable:

- persona portability
- lifecycle management
- governance readiness
- more explicit interoperability evaluation

The next practical step for POP is a canonical schema and validator that bind these semantics into a stable machine-checkable format.
