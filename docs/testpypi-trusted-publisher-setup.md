# TestPyPI Trusted Publisher Setup for POP

## Purpose

TestPyPI is the preferred first publication target because it allows the
full build, upload, and installation path to be smoke tested before a
real PyPI publication is attempted.

## Publication Strategy

- manual TestPyPI smoke first
- Trusted Publisher workflow second
- real PyPI publication only after TestPyPI success

## Required GitHub Side Preparation

- create a dedicated workflow file for TestPyPI publication
- use an optional but recommended environment named `testpypi`
- trigger the workflow with `workflow_dispatch`
- keep build and publish in separate jobs
- restrict permissions on the publish job

## Required TestPyPI Side Preparation

The repository workflow identity must be configured as a Trusted
Publisher on TestPyPI. The workflow name, repository, and environment
configuration must match the GitHub workflow definition.

## Security Notes

Trusted Publisher workflows should be treated as sensitive release
infrastructure. Separating build and publish jobs helps reduce the
effective trust surface and makes release review easier.

## First Smoke Checklist

- build `dist/`
- run `twine check`
- upload to TestPyPI
- verify the package page
- verify installation from TestPyPI in a clean virtual environment
- if strict schema validation is part of the smoke path, install
  `pop-persona[schema]` rather than the core package alone

## Transition to Real PyPI

Real PyPI publication should follow a successful TestPyPI smoke and the
existing tagged release discipline.
