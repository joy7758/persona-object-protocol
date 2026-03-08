# Changelog

This changelog tracks notable protocol, schema, SDK, adapter, fixture,
and documentation changes. As an early-stage project, entries may evolve
as governance practices mature.

## [Unreleased]

### Added

### Changed

- Runtime adapter release preparation continues while preserving the
  canonical schema baseline at `v0.1.0`.

### Fixed

## [0.1.2] - 2026-03-09

### Added

- Early LangChain runtime integration scaffold.
- Early CrewAI runtime integration scaffold.
- Integration examples for LangChain and CrewAI.
- Dependency-light integration contract tests.

### Changed

- Aligned runtime-facing integration bindings with existing
  adapter/projection surfaces.
- Documented `v0.1.2` as a runtime adapter release while preserving the
  canonical schema baseline at `v0.1.0`.

## [0.1.1] - 2026-03-09

### Fixed

- Bundled canonical schema resources into the installable package.
- Updated schema loading to work from installed package resources, not
  only source-tree assumptions.
- Restored installed-package visibility of available schema versions.
- Clarified the strict smoke installation path for the optional schema
  dependency.

## [0.1.0] - 2026-03-09

### Added

- Framework-neutral positioning for POP as a persona object protocol for
  agent runtimes.
- Ecosystem roadmap and adapter model documentation.
- Cross-runtime portability demo scaffolding.
- A minimal Python SDK for persona loading, validation, and projection.
- A canonical JSON Schema and strict validation path.
- Schema versioning with a current preview alias and a versioned
  historical snapshot.
- A valid and invalid fixture corpus for regression testing.
- A strict CI gate for schema validation and projection contracts.
