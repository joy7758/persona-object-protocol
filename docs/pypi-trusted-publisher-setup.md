# PyPI Trusted Publisher Setup for POP

## Purpose

This document records the repository-side and PyPI-side configuration
needed for the first real PyPI publication of `pop-persona`.

## Publication Strategy

- TestPyPI smoke remains the rehearsal path.
- Real PyPI publication uses a separate workflow identity.
- The first public PyPI upload should follow a tagged repository
  release, successful package checks, and successful TestPyPI smoke.

## Required GitHub Side Preparation

- workflow file: `.github/workflows/pypi-publish.yml`
- environment: `pypi`
- trigger: `workflow_dispatch`
- split `build` and `publish-pypi` jobs
- keep the publish job permissions minimal:
  - `id-token: write`

## Required PyPI Side Preparation

Create a pending Trusted Publisher for the `pop-persona` project on
PyPI. The workflow identity must match the repository-side
configuration.

Use these values:

- PyPI project name: `pop-persona`
- GitHub owner: `joy7758`
- GitHub repository: `persona-object-protocol`
- workflow file: `pypi-publish.yml`
- environment: `pypi`

If the project does not yet exist on PyPI, the first successful
Trusted Publishing run can create it. This does not reserve the project
name ahead of time, so the pending publisher should be followed by a
prompt publication run.

## Security Notes

Trusted Publisher workflows should be treated as sensitive release
infrastructure. Keeping build and publish as separate jobs reduces the
scope of the credential-bearing step and makes the publication path
easier to audit.

## First PyPI Smoke Checklist

- confirm `v0.1.3` (or the intended tag) is pushed
- confirm package-check and schema-gate workflows are green
- dispatch the `PyPI Publish` workflow manually
- confirm the project page appears on PyPI
- install `pop-persona[schema]` from PyPI in a clean virtual
  environment
- run `pop-inspect --list-schema-versions`
- run `pop-inspect --strict-schema` against a minimal valid persona

## Transition From TestPyPI

The PyPI workflow mirrors the TestPyPI workflow except for the target
repository. TestPyPI remains useful for future smoke rehearsals, but
the public PyPI release should be treated as the canonical distribution
event for each tagged package version.
