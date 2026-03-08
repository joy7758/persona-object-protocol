# POP Schema Migration Note: <from> -> <to>

## Summary

Provide a concise statement of what changed between the two schema
versions.

## Change Type

State one of:

- non-breaking
- conditionally breaking
- breaking

## Structural Changes

- added fields:
- removed fields:
- type changes:
- constraint changes:
- documentation-only clarifications:

## Impact on Existing Persona Objects

- what existing objects continue to validate:
- what objects may now fail validation:

## Adapter Implications

- LangChain projection impact:
- CrewAI projection impact:
- runtime-facing mapping changes:

## Fixture Updates

- new valid fixtures:
- new invalid fixtures:
- retired fixtures:

## Recommended Migration Steps

- [ ] identify affected persona objects
- [ ] validate objects against the new schema
- [ ] update runtime adapters if required
- [ ] refresh valid and invalid fixtures
- [ ] update regression tests
- [ ] document any unresolved compatibility risks

## Notes

- draft-stage caveats:
- unresolved issues:
