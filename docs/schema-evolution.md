# POP Schema Evolution Note

## Purpose

Schema evolution rules are needed because POP is a protocol draft rather
than a static example repository. Once a schema begins to serve as a
validation boundary, changes to that boundary must be described in a
disciplined way so that reviewers can distinguish clarifications from
compatibility risks.

## Current Status

POP currently provides an early preview canonical schema for persona
objects. The current preview alias is stored at
[`schema/pop-persona.schema.json`](../schema/pop-persona.schema.json),
while versioned schemas are stored under
[`schema/versions/`](../schema/versions/).

## Versioning Model

POP is still in a `v0.x` draft stage. During this phase, version numbers
should be interpreted as preview markers rather than as mature stability
guarantees.

- patch-like changes are limited to clarifications or corrections with
  no intended validation impact
- minor-like changes may add preview capabilities or optional structure
  without changing the meaning of existing valid objects
- major-like changes indicate a substantial compatibility boundary shift,
  even if preview-stage numbering remains conservative

This model is intentionally cautious. The protocol should not claim more
stability than its current review and adoption level can support.

## Compatibility Rules

- additive metadata changes are usually non-breaking
- adding new required top-level fields is breaking
- changing field types is breaking
- tightening validation constraints can be breaking
- clarifying descriptions without validation impact is non-breaking

## Object Version vs Schema Version

The persona object's `version` field is object-level data. It describes
the version carried by that object instance.

The `$schema` field identifies the structural contract used for
validation. These two fields should not be conflated: an object version
describes the object, while `$schema` identifies the schema resource
used to validate its structure.

## Required Governance Steps for Future Schema Changes

- create a new versioned schema snapshot
- update the current preview alias
- add valid and invalid fixtures
- update strict validation tests
- document migration notes if the change is breaking

## Future Direction

Future schema evolution may make use of `$defs` for more modular
structuring and controlled extension. At the current draft stage, the
priority is to keep the top-level boundary explicit and the governance
process reviewable.
