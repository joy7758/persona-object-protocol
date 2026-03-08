# POP Schema Migration Note: none -> v0.1.0

## Summary

`v0.1.0` establishes the first versioned baseline snapshot for POP
persona objects. It is the first normative structural reference for
strict validation, review, and comparison.

## Change Type

This change is best understood as baseline establishment. There is no
prior normative version to migrate from.

## Structural Boundary Established

The v0.1.0 baseline defines a canonical POP persona object with the
following top-level fields:

- `id`
- `version`
- `name`
- `summary`
- `traits`
- `communication_style`
- `task_orientation`
- `boundaries`
- `preferred_outputs`
- `metadata`

This baseline also establishes the canonical JSON Schema, the strict
validation path in the SDK, and fixture-backed regression discipline.

## Impact on Existing Persona Objects

Pre-release examples may need explicit `$schema` alignment in order to
participate in strict validation and schema-governed review.

Only objects that conform to the canonical structural boundary should be
treated as POP-valid under strict validation.

## Adapter Implications

LangChain and CrewAI projections remain adapter-facing views of the
canonical persona object. Adapters do not redefine POP core semantics;
they only bind canonical persona data to runtime-facing abstractions.

## Fixture and Validation Implications

The fixture corpus now distinguishes valid and invalid samples, and the
strict CI schema gate treats those fixtures as regression evidence.

## Recommended Operator Steps

- add `$schema` to canonical examples
- run strict validation
- review the fixture corpus
- confirm the CLI and package-check workflow pass

## Notes

This remains an early preview baseline. Future versions may evolve under
the schema governance discipline now defined in this repository.
