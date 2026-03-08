# Changelog

This changelog tracks notable protocol, schema, SDK, adapter, fixture,
and documentation changes. As an early-stage project, entries may evolve
as governance practices mature.

## [Unreleased]

### Added

### Changed

### Fixed

## [0.1.5] - 2026-03-09

### Added

- LangChain execution contract work centered on
  `create_langchain_execution_bundle(...)`.
- Installed-package and optional-dependency smoke paths for the
  LangChain contract surface.

### Changed

- Documented `v0.1.5` as a LangChain execution contract release while
  the canonical schema baseline remains `v0.1.0`.
- Clarified that CrewAI remains compatibility-focused and secondary in
  this release line.

## [0.1.4] - 2026-03-09

### Added

- LangChain optional-dependency execution helpers aligned with
  `create_agent`, middleware, and runtime-context helper surfaces.
- A LangChain optional-dependency helper that reports whether the
  `langchain` extra is available and returns a dependency-aware spec.
- A `langchain_create_agent_minimal.py` example for local execution-side
  scaffolding.
- LangChain execution bundle and optional-dependency tests that keep the
  helper surface dependency-light by default.

### Changed

- Documented `v0.1.4` as a LangChain optional-dependency execution
  release while preserving the canonical schema baseline at `v0.1.0`.
- Clarified that CrewAI remains compatibility-focused and secondary in
  this release line.
- Lowered legacy LangChain scaffold helpers to backward-compatibility
  status in the documentation surface.

## [0.1.3] - 2026-03-09

### Added

- Early LangChain execution-layer helpers for agent kwargs, middleware,
  and execution scaffolds.
- Early CrewAI execution-layer helpers for Agent-style kwargs and
  execution scaffolds.
- Execution-layer examples for LangChain and CrewAI.
- Dependency-light smoke tests for execution-layer helper surfaces.
- Execution-layer planning and release documentation.

### Changed

- Extended runtime-facing integration helpers without changing the
  canonical top-level persona boundary.
- Documented `v0.1.3` as an execution-layer release while preserving
  the canonical schema baseline at `v0.1.0`.

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
