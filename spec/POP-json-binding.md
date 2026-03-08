# POP v1.0 JSON Binding

Draft Specification

Status: Work in progress. This document defines the canonical JSON binding for POP v1.0 core persona objects.

Companion semantics reference: [`POP-core.md`](./POP-core.md) and the archived POP-Core paper at `https://doi.org/10.5281/zenodo.18907957`.

## 1. Purpose

This document binds the abstract POP core model to a concrete JSON representation.

The POP core model defines semantic fields such as identity, role, boundaries, status, provenance, and version. This document defines how those semantics are serialized as a canonical JSON object.

This binding is intended for:

- schema validation
- interoperation across runtimes
- compatibility mapping from earlier POP drafts

## 2. Canonical JSON Object

A POP v1.0 core persona object is serialized as a JSON object with the following required fields:

| Field | JSON Type | Required | Meaning |
| --- | --- | --- | --- |
| `kind` | string | yes | object kind discriminator |
| `id` | string | yes | stable object identifier |
| `version` | string | yes | object revision identifier |
| `role` | string | yes | primary persona role label |
| `traits` | array of strings | yes | durable descriptive tendencies |
| `boundaries` | object | yes | named boundary constraints |
| `status` | string | yes | lifecycle state |
| `provenance` | object | yes | origin and issuance metadata |

Canonical example:

```json
{
  "kind": "persona-object",
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

## 3. Field Semantics

### 3.1 `kind`

`kind` MUST be the string `persona-object`.

This field distinguishes POP core persona objects from future related object kinds such as templates or policy objects.

### 3.2 `id`

`id` MUST be a stable identifier within the implementation's scope.

Implementations SHOULD use a URI-like namespace such as:

```text
persona:mentor:v1
```

`id` identifies the object across runtimes. It is not a user account identifier and MUST NOT be interpreted as identity proof.

### 3.3 `version`

`version` identifies the revision of the persona object itself.

`version` is an object version, not a protocol version.

Protocol version is determined by the validating schema, binding context, or surrounding specification, not by reusing the object's `version` field.

### 3.4 `role`

`role` captures the primary persona role label in compact form.

Examples:

- `mentor`
- `teacher`
- `caregiver`

`role` SHOULD remain stable across runtimes and SHOULD NOT be used as a long prompt payload.

### 3.5 `traits`

`traits` is an array of concise strings describing durable persona tendencies.

Examples:

- `calm`
- `analytical`
- `structured`

`traits` SHOULD represent stable descriptors rather than transient session instructions.

### 3.6 `boundaries`

`boundaries` defines named persona constraints.

Boundary entries MUST be interpreted as scope constraints or authority limits. They MUST NOT be interpreted as capability grants by themselves.

The canonical JSON binding supports two forms:

1. Boolean shorthand
2. Structured boundary object

Boolean shorthand example:

```json
{
  "financial_advice": false
}
```

Structured example:

```json
{
  "medical_advice": {
    "decision": "requires-review",
    "reason": "Requests in regulated domains must be escalated to qualified humans."
  }
}
```

### 3.7 `status`

`status` captures the lifecycle state of the object.

The canonical schema defines the following status values:

- `draft`
- `active`
- `deprecated`
- `replaced`
- `revoked`

### 3.8 `provenance`

`provenance` captures origin metadata for audit and traceability.

The canonical binding requires a creation timestamp and SHOULD include an author or issuer.

Typical provenance keys include:

- `author`
- `issuer`
- `created`
- `updated`
- `source`
- `license`
- `legacy_source`

## 4. Boundary Value Forms

### 4.1 Boolean Form

A boolean boundary value is a compact shorthand for common cases.

- `false` indicates the persona object does not claim authority in the named area.
- `true` indicates the named area is not prohibited by the persona object, but it still does not grant runtime permission.

Implementations MUST intersect persona boundaries with separate runtime policy and permission systems.

### 4.2 Structured Form

A structured boundary object supports more explicit modeling:

| Field | Type | Meaning |
| --- | --- | --- |
| `decision` | string | boundary decision |
| `reason` | string | optional human-readable explanation |
| `scope` | array of strings | optional scoped qualifiers |

The canonical schema defines these structured decisions:

- `allow`
- `disallow`
- `requires-review`
- `out-of-scope`
- `unspecified`

## 5. Validation

The canonical machine-readable schema for this binding is:

[`schema/pop.schema.json`](../schema/pop.schema.json)

Implementations claiming POP-Core support SHOULD validate persona objects against this schema or an equivalent normative schema.

## 6. Compatibility with `pop-0.1`

The existing `pop-0.1` repository artifacts are treated as legacy draft objects, not as the canonical POP v1.0 binding.

Compatibility mapping from `pop-0.1` to POP v1.0 is best-effort and may be lossy.

| `pop-0.1` field | POP v1.0 treatment | Notes |
| --- | --- | --- |
| `schema_version` | external validation context | not a canonical v1.0 top-level field |
| `id` | `id` | preserved directly where available |
| `name` | fallback input to `role` | use only if no explicit role anchor exists |
| `anchors[type=role]` | `role` | preferred role source |
| `traits` | `traits` | preserved directly |
| `behavior.tone` | optional trait compaction | MAY be folded into `traits` if needed |
| `behavior.interaction_style` | optional trait compaction | MAY be compacted into stable descriptors |
| `anchors[type=boundary]` | `boundaries` | normalize into named boundary entries |
| `behavior.boundaries` | `boundaries` | normalize into named boundary entries |
| `description` | no direct core equivalent | retain only in a companion schema or migration notes |
| `memory_hooks` | out of POP core scope | move to companion schemas or runtime-specific profiles |
| `plugins` | out of POP core scope | move to companion schemas or runtime-specific profiles |

Implementations performing migration SHOULD preserve the original source reference in `provenance.legacy_source` when available.

## 7. Serialization Guidance

Implementations SHOULD:

- emit fields in a stable order where feasible
- preserve `id`, `version`, `role`, `status`, and `boundaries` exactly during round-trip conversion
- keep narrative prompt text outside the core binding unless defined by a companion schema

Implementations MUST NOT:

- treat `role` or `traits` as permission grants
- embed live memory contents inside the core object
- treat provenance as identity proof unless defined by a separate verification system

## 8. Relationship to POP Core

This document is a JSON binding for the semantic model defined in [`spec/POP-core.md`](./POP-core.md).

If a conflict exists between semantic requirements in POP Core and convenience shortcuts in a runtime-specific adapter, POP Core semantics take precedence.
