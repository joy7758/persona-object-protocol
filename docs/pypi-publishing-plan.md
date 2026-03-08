# POP PyPI Publishing Plan

## Purpose

PyPI publication is useful because it provides a standard distribution
surface for the POP SDK. It should follow protocol governance readiness
rather than run ahead of schema discipline, fixture coverage, or release
review.

## Current Status

The package is PyPI-ready in structure, but automated publication is not
yet enabled for production use.

## Recommended Publication Path

- create or reserve the project name on PyPI
- configure a Trusted Publisher for GitHub Actions
- verify package build and `twine check` in CI
- publish to TestPyPI first if additional rehearsal is needed
- publish a stable draft release only after repository release and tag
  discipline is in place

## Trusted Publishing Rationale

Trusted Publishing uses OIDC-based identity from GitHub Actions. This is
preferable to long-lived API tokens because it reduces secret handling
risk and ties publication to a reviewed workflow identity.

## Pre-Publish Checklist

- changelog updated
- schema snapshot confirmed
- fixtures green
- strict CI green
- `dist/` build passes
- `twine check` passes
- release tag prepared

## Deferred Items

Signed attestations and more advanced publication automation can be
added later once the base release process is stable.
