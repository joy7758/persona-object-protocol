# POP 0.1 Draft Specification

## Abstract

Persona Object Protocol (POP) is a lightweight draft protocol for representing portable persona objects in future multimodal AI systems. POP defines a compact object format with a persona core, optional memory hooks, optional plugin attachment entry points, and a basic safety boundary. POP does not define persona generation algorithms, model training methods, or runtime orchestration.

## Design goals

- Keep the object structure compact and inspectable.
- Separate persona representation from memory, permissions, and execution.
- Support conservative portability across multimodal systems.
- Provide attachment points for plugins without turning the protocol into a tool runtime.
- Make governance boundaries explicit at the object layer.

## Non-goals

- Defining persona generation algorithms.
- Defining model training, fine-tuning, or inference methods.
- Defining memory storage or retrieval behavior.
- Defining permission grants or agent execution policies.
- Guaranteeing high-fidelity persona transfer across vendors, models, or products.

## Core concepts

### Persona Object

A POP object is a JSON document that describes a persona in a portable, bounded form.

### Persona Core

The Persona Core contains the minimum descriptive fields required to identify and characterize the persona object:

- `schema_version`
- `id`
- `name`
- `description`
- `traits`
- `anchors`
- `behavior`

### Memory Hooks

Memory Hooks are declarative references to external memory subsystems. A POP object may declare where memory integration can occur, but it does not carry the memory itself and does not define retrieval or ranking logic.

### Plugin Manifest

The Plugin Manifest is a list of optional attachment entry points. Plugin entries advertise intended integrations, but they do not grant permissions and do not require any given runtime.

### Safety Boundary

The Safety Boundary is the rule that a persona object must remain separate from:

- memory contents
- permission grants
- identity proof
- operator policy
- claims of human equivalence or continuity

## Persona Core

The Persona Core should capture stable, portable framing rather than large prompt payloads.

- `traits` lists concise persona descriptors.
- `anchors` records salient role or boundary statements.
- `behavior` records interaction tone, style, and limits.

Implementations should prefer durable descriptors over product-specific prompt instructions.

## Memory Hooks

`memory_hooks` is an array of declarative references. Each entry should identify:

- a hook identifier
- a hook type
- a short description
- an optional reference string

POP does not define memory schemas, memory permissions, or retention policy.

## Plugin Manifest

`plugins` is an array of declarative plugin entries. Each entry should identify:

- a plugin name
- an entry point
- optional capability labels

Plugin entries are descriptive only. They do not authorize execution, install software, or override host security controls.

## Safety Boundary

A POP object should be interpreted as a portable persona object draft, not as a person, account, agent runtime, or legal authority. Implementations should keep consent, audit, access control, and safety policy in adjacent systems rather than embedding them into the persona object itself.

POP is a draft protocol and not a guarantee of high-fidelity persona transfer.

## Versioning

This draft uses the string `pop-0.1` in `schema_version`. Implementations should compare the full version string and treat unknown versions conservatively. During the `0.x` phase, incompatible changes may occur between draft revisions.

## Example object

```json
{
  "schema_version": "pop-0.1",
  "id": "urn:pop:mentor:structured-guidance",
  "name": "Structured Mentor",
  "description": "A mentor persona oriented toward practical guidance and steady skill development.",
  "traits": ["patient", "structured", "clear"],
  "anchors": [
    { "type": "role", "value": "skill-building mentor" },
    { "type": "boundary", "value": "does not claim professional certification" }
  ],
  "behavior": {
    "tone": "calm and direct",
    "interaction_style": ["goal setting", "stepwise feedback"],
    "boundaries": ["keeps claims modest", "does not provide legal or medical advice"]
  },
  "memory_hooks": [
    {
      "id": "progress-log",
      "type": "summary-reference",
      "description": "Optional pointer to an external progress summary store",
      "ref": "memory://progress-log"
    }
  ],
  "plugins": [
    {
      "name": "lesson-planner",
      "entry_point": "plugin://lesson-planner",
      "capabilities": ["plan-outline"]
    }
  ]
}
```
