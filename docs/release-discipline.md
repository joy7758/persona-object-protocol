# POP Release and Tagging Discipline

## Purpose

Release discipline matters because POP is a draft protocol project rather
than a one-off software artifact. Tags, release notes, schema snapshots,
fixtures, and package builds together form the auditable surface of a
protocol release.

## Tagging Model

Git tags are the release anchor for the repository. Recommended tag
shapes include:

- `v0.1.0`
- `v0.1.1`
- `v0.2.0`

## Repository Release, Schema Version, and Python Package Version

Repository releases, schema versions, and Python package versions are
related, but they are not automatically identical.

- a repository release describes the state of the overall project
- a schema version identifies a structural contract snapshot
- a Python package version identifies a distributable SDK build

These may move together in simple cases, but they should still be
reviewed as separate version surfaces.

## Draft-Stage Versioning Guidance

- patch-like changes cover documentation corrections, fixture updates,
  or implementation refinements that do not intentionally alter the
  protocol boundary
- minor-like changes add preview capabilities or new draft surfaces
  while aiming to preserve current objects where practical
- breaking draft evolution changes the schema boundary, the SDK contract,
  or adapter expectations in a way that requires migration review

## Release Checklist

- schema snapshot confirmed
- fixture corpus updated
- tests and strict CI green
- changelog updated
- migration note added if needed
- package build passes
- `twine check` passes

## GitHub Releases

GitHub releases should be created from tags. Release notes should
summarize protocol, schema, SDK, adapter, fixture, and documentation
changes in a concise reviewable form.

## PyPI Publication Readiness

Package publication should follow repository release discipline, not
replace it. A package upload is one distribution step within the release
process, not the sole source of release truth.
