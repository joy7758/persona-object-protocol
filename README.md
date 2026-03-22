<!-- language-switch:start -->
<p>
  <a href="./README.md">
    <img src="https://img.shields.io/badge/English-Current-1f883d?style=for-the-badge" alt="English">
  </a>
  <a href="./README.zh-CN.md">
    <img src="https://img.shields.io/badge/Chinese-Switch-0f172a?style=for-the-badge" alt="Chinese">
  </a>
</p>
<!-- language-switch:end -->

# Persona Object Protocol (POP)

[![CI](https://github.com/joy7758/persona-object-protocol/actions/workflows/validate.yml/badge.svg)](https://github.com/joy7758/persona-object-protocol/actions/workflows/validate.yml)
[![PyPI](https://img.shields.io/pypi/v/pop-persona)](https://pypi.org/project/pop-persona/)
[![Python](https://img.shields.io/pypi/pyversions/pop-persona)](https://pypi.org/project/pop-persona/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18907957.svg)](https://doi.org/10.5281/zenodo.18907957)
[![Release](https://img.shields.io/github/v/release/joy7758/persona-object-protocol)](https://github.com/joy7758/persona-object-protocol/releases)
[![License](https://img.shields.io/github/license/joy7758/persona-object-protocol)](./LICENSE)

A portable persona object layer for the Digital Biosphere Architecture.

## Role

`persona-object-protocol` is the persona layer of the Digital Biosphere Architecture. It defines portable persona objects, projection rules, and persona attachment surfaces across runtimes.

## Not this repo

- not the governance layer
- not the audit layer
- not the benchmark suite
- not the architecture hub

## Start here

- [TRY_POP.md](TRY_POP.md)
- [docs/cite-pop.md](docs/cite-pop.md)
- [digital-biosphere-architecture](https://github.com/joy7758/digital-biosphere-architecture)

## Depends on

- [digital-biosphere-architecture](https://github.com/joy7758/digital-biosphere-architecture)
- [agent-intent-protocol](https://github.com/joy7758/agent-intent-protocol)
- optional runtime integrations such as LangChain and CrewAI

## Status

- active persona layer
- protocol-first surface
- runtime integrations remain secondary to the canonical POP model

## Role in Digital Biosphere Architecture

POP is the **Persona Object Standard Entry**.

It defines the canonical structure of persona objects used by autonomous agents.

Position in architecture:

Persona Layer -> POP

## A lightweight draft protocol for portable persona objects in multimodal AI systems

POP is the Persona Layer of the [Digital Biosphere Architecture](https://github.com/joy7758/digital-biosphere-architecture). It focuses on one layer of the broader architecture rather than a full agent stack. POP is a framework-agnostic persona object protocol built as a reusable interface and projection model for portable persona objects with explicit boundaries.

It is positioning-first and protocol-oriented: not a product, not a persona generation pipeline, and not a full runtime stack.

Preferred scholarly citation for POP is the POP-Core paper: [10.5281/zenodo.18907957](https://doi.org/10.5281/zenodo.18907957).

The repository itself is separately archived on Zenodo at [10.5281/zenodo.18898252](https://doi.org/10.5281/zenodo.18898252) for version-specific software citation.

For minimal citation guidance, see [`docs/cite-pop.md`](docs/cite-pop.md).

## Architecture Context

This repository is a focused layer in the [Digital Biosphere Architecture](https://github.com/joy7758/digital-biosphere-architecture) ecosystem.
It does not try to be the full stack.
It contributes the Persona Layer for verifiable AI systems.
Its focus is portable persona objects, reusable projection surfaces, and identity attachment across runtimes.

## Relationship to Adjacent Repositories

POP is the persona-layer interface and projection model in the broader stack. It is not the full architecture, not the audit layer, and not a generic end-to-end demo. For the system view, start with [digital-biosphere-architecture](https://github.com/joy7758/digital-biosphere-architecture); for the walkthrough path, see [verifiable-agent-demo](https://github.com/joy7758/verifiable-agent-demo); for adjacent lower-level protocol work around structured agent objects, see [agent-object-protocol](https://github.com/joy7758/agent-object-protocol).

## First Trial

Want to try POP quickly without setting up a full runtime?
Start here:

- [Try POP in 3 Minutes](TRY_POP.md)

This dry-run demo shows 3 portable persona objects projected into 3
CrewAI-style runtime roles.

## Plugin Discovery

The demo workflow can load registry extensions from builtin modules and
external plugin packages. By default, the runtime looks for a local
`plugin_config.json` file at the repository root if present. An example
template is available at [`plugin_config.example.json`](plugin_config.example.json),
and the config shape is defined by
[`plugin_config.schema.json`](plugin_config.schema.json). A second example,
[`plugin_config.packages.example.json`](plugin_config.packages.example.json),
shows the variant where package names and package search paths are listed separately.
The example config is also validated in CI so schema drift is caught during PR review.

For temporary overrides, you can also point discovery at external plugin
packages with `POP_PLUGIN_CONFIG_FILE`, `POP_PLUGIN_PACKAGES`, and
`POP_PLUGIN_PACKAGE_PATHS`.

If you use file-based plugin config validation outside this repository,
install the optional schema dependency:

```bash
pip install "pop-persona[schema]"
```

### Plugin Extension Tutorial

The demo registry loads definitions from three extension surfaces:

- `STAGE_HANDLER_DEFINITIONS` for stage handlers
- `PERSONA_DEFINITIONS` for builtin or external persona registry entries
- `TASK_TYPE_DEFINITIONS` for task-type metadata and stage routing

Discovery order is:

1. builtin `demos` modules
2. packages from `plugin_config.json` or `POP_PLUGIN_CONFIG_FILE`
3. package names and search paths from `POP_PLUGIN_PACKAGES` and `POP_PLUGIN_PACKAGE_PATHS`

Environment variables act as an override layer on top of file-based config.

#### Config Shape 1: `plugin_paths`

Use this when each plugin package is easiest to describe as a single
`path` plus `package_name` pair.

```json
{
  "$schema": "./plugin_config.schema.json",
  "plugin_paths": [
    {
      "path": "/tmp/pop_demo_plugins",
      "package_name": "pop_demo_plugins"
    }
  ],
  "plugin_packages": [],
  "plugin_package_paths": []
}
```

This is the shape shown in
[`plugin_config.example.json`](plugin_config.example.json).

#### Config Shape 2: `plugin_packages` + `plugin_package_paths`

Use this when package names and import search paths need to be managed
separately.

```json
{
  "$schema": "./plugin_config.schema.json",
  "plugin_paths": [],
  "plugin_packages": [
    "pop_demo_plugins",
    "pop_extra_plugins"
  ],
  "plugin_package_paths": [
    "./plugins/pop_demo_plugins",
    "./plugins/pop_extra_plugins"
  ]
}
```

This is the shape shown in
[`plugin_config.packages.example.json`](plugin_config.packages.example.json).

#### Field Notes

- `plugin_paths`: Array of either plain path strings or objects with `path` and optional `package_name`.
- `plugin_packages`: Import package names to scan for `*_DEFINITIONS` exports.
- `plugin_package_paths`: Filesystem paths added to `sys.path` before plugin package imports.
- `path`: A relative path is resolved from the config file directory; an absolute path is used as-is.
- `package_name`: Optional for `plugin_paths` entries, but required if the path alone is not enough to identify the package to import.

#### How To Add A Plugin Package

1. Create a Python package that exposes one or more of:
   `STAGE_HANDLER_DEFINITIONS`, `PERSONA_DEFINITIONS`, `TASK_TYPE_DEFINITIONS`.
2. If a persona definition points to a JSON file, keep the JSON inside the
   plugin package and set `package_name` on the `PersonaDefinition` so the
   runtime can resolve the relative file path correctly.
3. Add the package to `plugin_config.json`, or point the runtime at it with
   `POP_PLUGIN_CONFIG_FILE`, `POP_PLUGIN_PACKAGES`, and `POP_PLUGIN_PACKAGE_PATHS`.
4. Run the demo against a task that references the new `task_type`.

Example:

```bash
POP_PLUGIN_CONFIG_FILE=/tmp/pop_demo_plugins/plugin_config.json \
python demos/persona_workflow_demo.py --task-input /tmp/content_strategy_task.json
```

## Persona Layer Diagram

```mermaid
flowchart TD
    A[Persona Ref] --> B[POP Persona Object]
    B --> C[Resolve / Validate]
    C --> D[Runtime Projection]
    D --> E[CrewAI]
    D --> F[LangChain]
    D --> G[AutoGen]

    H[POP treats persona as a portable object layer for agent runtimes.<br/>Framework configs are derived projections.]:::note

    B --- H

    classDef note fill:#f6f8fa,stroke:#d0d7de,color:#24292f,font-size:12px;
```

Static assets: [SVG](docs/assets/pop-persona-layer-diagram.svg) · [PNG](docs/assets/pop-persona-layer-diagram.png)

## Design Position

POP defines a portable persona object layer for agent runtimes.

The protocol focuses on representing persona as a standalone object that can be referenced, resolved, validated, and projected into different runtime environments.

Runtime configurations such as CrewAI agents or other framework-specific configs are derived projections rather than the protocol core.

This separation keeps persona definitions portable across agent frameworks while runtime environments remain free to implement their own execution models.

## Positioning

- POP is not a full agent framework.
- POP is not a prompt template library.
- POP is not a memory or permissions system.
- POP does not define task intent objects.
- POP does not define action exchange objects.
- POP does not define result exchange objects.
- POP focuses on portable persona objects and adapter-based runtime projection.

## Relationship to the Interaction Layer

POP defines who the agent is.
The Interaction Layer defines what is being requested or attempted.
This separation keeps identity distinct from task semantics.

For the interaction-layer draft in the broader ecosystem, see [Agent Intent Protocol](https://github.com/joy7758/agent-intent-protocol).

## Ecosystem Direction

- LangChain integration
- CrewAI projection
- Microsoft Agent Framework exploration
- LlamaIndex exploration

For the current ecosystem plan, see [`docs/pop-ecosystem-roadmap.md`](docs/pop-ecosystem-roadmap.md).
For the adapter strategy, see [`docs/pop-adapter-model.md`](docs/pop-adapter-model.md).

## Runtime Adapter Layer

The runtime-facing adapter surface is documented in
[`docs/runtime-adapters.md`](docs/runtime-adapters.md). The current
LangChain and CrewAI adapters are early-preview scaffolds that bind
canonical POP persona objects to runtime-oriented representations
without changing the schema baseline.

## Runtime Integrations (Early Preview)

LangChain integration scaffolds are available through the optional
`langchain` extra, and CrewAI integration scaffolds are available
through the optional `crewai` extra. The canonical schema baseline
remains `v0.1.0` while runtime-facing binding surfaces continue to
evolve.

Install examples:

```bash
pip install "pop-persona[langchain]"
pip install "pop-persona[crewai]"
```

Example scripts:

- [`examples/integrations/langchain_minimal.py`](examples/integrations/langchain_minimal.py)
- [`examples/integrations/crewai_minimal.py`](examples/integrations/crewai_minimal.py)

## POP → CrewAI Prototype

This repository includes an early POP → CrewAI adapter prototype.

Current capabilities:

- load POP personas from JSON
- convert POP personas into CrewAI-compatible agent configuration
- export CrewAI YAML from POP persona objects

Example persona files:

- `personas/marketing_manager.json`
- `personas/engineer.json`
- `personas/designer.json`

Generated example:

- `personas/marketing_manager.crewai.yaml`

Example scripts:

- `example_crewai.py`
- `example_crewai_export.py`

Current scope:

- local persona loading
- CrewAI config generation
- YAML export for CrewAI-style configuration

This is an early adapter prototype intended to demonstrate POP as an
agent-framework persona layer.

### CrewAI YAML Export

POP personas can also be exported into CrewAI-style multi-agent YAML
configuration.

Example:

- `example_crewai_multiagent_export.py`
- generated file: `personas/agents.crewai.yaml`

This makes POP usable not only for direct agent construction, but also
for CrewAI's recommended YAML-based configuration flow.

### CrewAI Recommended YAML Flow

CrewAI documentation recommends YAML configuration for defining agents.
POP can now export multi-agent YAML that fits this path.

Demo files:

- `examples/crewai_config_demo/config/agents.yaml`
- `examples/crewai_config_demo/crew_example.py`

This demonstrates:

POP personas -> CrewAI-style `agents.yaml` -> config-based agent
construction

### CrewAI CrewBase-Style Demo

CrewAI documentation recommends YAML-based agent configuration, with
YAML keys matching method names in Python code.

This repository now includes a POP-driven CrewBase-style demo:

- `examples/crewai_crewbase_demo/config/agents.yaml`
- `examples/crewai_crewbase_demo/crew_demo.py`

This demonstrates:

POP personas -> CrewAI-style `agents.yaml` -> method-aligned
CrewBase-style Python structure

### AutoGen-Aligned Prototype

This repository includes an early POP -> AutoGen adapter prototype
aligned with the current AutoGen quickstart shape:

- `AssistantAgent`
- `model_client`
- `tools`
- `system_message`

Example:

- `example_autogen.py`

Current capabilities:

- map POP personas into AutoGen-style config
- generate `system_message` from persona objects
- return a safe preview object if AutoGen is not installed
- require an explicit `model_client` for real `AssistantAgent`
  construction

Recommended AutoGen installation (upstream style):

```bash
pip install -U "autogen-agentchat" "autogen-ext[openai,azure]"
```

## POP Agent Runtime Profile

This repository now distinguishes between:

- POP canonical persona objects (protocol-layer objects)
- POP Agent Runtime Profiles (framework-facing runtime bindings)

The current `personas/*.json` examples are treated as Agent Runtime
Profiles for agent frameworks such as CrewAI and AutoGen.

Related files:

- `spec/POP-agent-runtime-profile.md`
- `schema/profiles/pop-agent-runtime-profile.schema.json`

## POP Registry / SDK Prototype

This repository includes an early local registry / SDK prototype for
persona objects.

Current capabilities:

- `list_personas()` to enumerate local persona files
- `list_persona_ids()` to enumerate local persona IDs
- `resolve_persona(persona_ref)` to map persona references to files
- `load_persona_by_id(...)` to load personas through the registry
- `validate_persona(...)` to perform minimal validation

Example:

- `example_registry.py`

### Persona ID / URI convention (prototype)

The POP registry prototype now supports normalized persona references.

Examples:

- `marketing_manager_v1`
- `pop:marketing_manager_v1`

This is an early prototype for stable persona identifiers in POP-based
tooling. The current implementation normalizes `pop:<persona_id>`
references into local registry resolution, preparing for future
URI-based registry evolution.

## Execution-Layer Helpers (Early Preview)

LangChain execution helpers are available through optional runtime
integration surfaces, and CrewAI execution helpers are available
through optional runtime integration surfaces. The canonical schema
baseline remains `v0.1.0`.

Execution-layer examples:

- [`examples/integrations/langchain_create_agent_minimal.py`](examples/integrations/langchain_create_agent_minimal.py)
- [`examples/integrations/langchain_execution_minimal.py`](examples/integrations/langchain_execution_minimal.py)
- [`examples/integrations/crewai_execution_minimal.py`](examples/integrations/crewai_execution_minimal.py)

## LangChain Execution Contract (Early Preview)

LangChain execution helpers are available through the optional
`langchain` extra. They are aligned with LangChain v1
`create_agent`, middleware, and runtime-context helper surfaces, but
they are not official LangChain runtime objects. The canonical schema
baseline remains `v0.1.0`.

The main LangChain-facing entry point in this release line is
`create_langchain_execution_bundle(...)`. Optional `langchain` support
enables richer helper/spec paths, while compatibility helpers remain
available but are no longer the primary documented path.

LangChain contract examples:

- [`examples/integrations/langchain_create_agent_minimal.py`](examples/integrations/langchain_create_agent_minimal.py)
- [`examples/integrations/langchain_execution_minimal.py`](examples/integrations/langchain_execution_minimal.py)
- [`examples/integrations/langchain_installed_contract_minimal.py`](examples/integrations/langchain_installed_contract_minimal.py)

Compatibility helpers from the earlier execution scaffolding line are
retained for backward compatibility. The primary LangChain-facing
surface in the current release line is:

- `create_langchain_execution_bundle(...)`
- `create_langchain_create_agent_kwargs(...)`
- `create_langchain_context_bundle(...)`
- `create_langchain_middleware_bundle(...)`
- `maybe_build_langchain_agent_spec(...)`

## LangChain Minimal Adoption (Early Preview)

The primary LangChain-facing entry point remains
`create_langchain_execution_bundle(...)`. This path is designed to
reduce first-adoption friction and to keep installed-package smoke
validation easy to reproduce.

Compatibility helpers remain available for backward compatibility, but
they are not the recommended primary path for first adoption. The
canonical schema baseline remains `v0.1.0`.

Minimal-adoption references:

- [`examples/integrations/langchain_minimal_20_lines.py`](examples/integrations/langchain_minimal_20_lines.py)
- [`examples/integrations/langchain_installed_smoke_minimal.py`](examples/integrations/langchain_installed_smoke_minimal.py)
- [`docs/quickstart/langchain-minimal-adoption.md`](docs/quickstart/langchain-minimal-adoption.md)

## Portability Demo

An early cross-runtime portability scaffold is available at
[`examples/cross-runtime-persona-portability/README.md`](examples/cross-runtime-persona-portability/README.md).

## Canonical JSON Schema

POP provides a canonical JSON Schema for persona objects at
[`schema/pop-persona.schema.json`](schema/pop-persona.schema.json).
The current schema is an early preview intended to define the core
structural boundary of a POP persona object. Within that boundary,
persona remains separate from memory, tools, and permissions.

`schema/pop-persona.schema.json` is the current preview alias.
[`schema/versions/`](schema/versions/) contains versioned historical
snapshots, and those versioned schemas are the normative references for
stable review and comparison.

Valid and invalid fixtures are maintained under [`fixtures/valid/`](fixtures/valid/)
and [`fixtures/invalid/`](fixtures/invalid/) to support strict
validation and protocol regression testing.

## Release Baseline

`v0.1.0` is the first tagged baseline release for POP. Versioned schemas
under [`schema/versions/`](schema/versions/) are the normative
snapshots, while the current alias continues to track the latest preview
surface.

TestPyPI smoke and Trusted Publishing setup are part of the
release-readiness path for this baseline.

For the current public packaging position, see
[`docs/releases/v0.1.1-announcement.md`](docs/releases/v0.1.1-announcement.md).
The runtime adapter release is documented at
[`docs/releases/v0.1.2-release-notes.md`](docs/releases/v0.1.2-release-notes.md).
The current execution-layer release is documented at
[`docs/releases/v0.1.7-release-notes.md`](docs/releases/v0.1.7-release-notes.md).
A public release announcement is available in
English at [`docs/releases/v0.1.5-announcement.md`](docs/releases/v0.1.5-announcement.md)
and in Chinese at
[`docs/releases/v0.1.5-announcement.zh.md`](docs/releases/v0.1.5-announcement.zh.md).
For a maintainer-facing LangChain summary, see
[`docs/langchain-maintainer-note.md`](docs/langchain-maintainer-note.md).
The previous execution-layer increment remains documented at
[`docs/releases/v0.1.3-release-notes.md`](docs/releases/v0.1.3-release-notes.md).
The LangChain contract-focused release plan is documented in
[`docs/releases/v0.1.5-plan.md`](docs/releases/v0.1.5-plan.md).
The next positioning draft is documented in
[`docs/releases/v0.1.6-plan.md`](docs/releases/v0.1.6-plan.md).
The early release chronology is summarized in
[`docs/pop-evolution-v0.1.0-v0.1.4.md`](docs/pop-evolution-v0.1.0-v0.1.4.md).

## Outreach and Evaluation Materials

- [`docs/outreach/langchain-forum-post.md`](docs/outreach/langchain-forum-post.md)
- [`docs/outreach/langchain-maintainer-short-note.md`](docs/outreach/langchain-maintainer-short-note.md)
- [`docs/outreach/langchain-evaluation-checklist.md`](docs/outreach/langchain-evaluation-checklist.md)
- [`docs/releases/v0.1.8-options.md`](docs/releases/v0.1.8-options.md)

## TestPyPI and Trusted Publishing

TestPyPI is used for first publication smoke validation. Trusted
Publishing is planned through GitHub Actions with OIDC, and real PyPI
publication follows successful smoke validation and release discipline.

## PyPI Publication Path

Real PyPI publication is prepared through a dedicated GitHub Actions
workflow and a separate `pypi` environment. The recommended order is:
configure the PyPI Trusted Publisher, dispatch the PyPI publish
workflow, and then validate installation from the public PyPI index in a
clean virtual environment.

## Python SDK (Early Preview)

A minimal Python SDK is provided as an early preview for loading,
validating, and projecting canonical POP persona objects.

Install from the repository root:

```bash
pip install -e .
```

Strict schema validation is available through an optional dependency:

```bash
pip install -e '.[schema]'
pip install "pop-persona[schema]"
```

For package build and release-readiness checks:

```bash
pip install -e '.[dev,schema]'
```

CLI example:

```bash
pop-inspect examples/cross-runtime-persona-portability/personas/lawyer_persona.json
pop-inspect --list-schema-versions
pop-inspect --strict-schema examples/cross-runtime-persona-portability/personas/lawyer_persona.json
```

Core installation provides lightweight inspection. Strict schema
validation requires the optional `schema` extra.

TestPyPI smoke example:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple "pop-persona[schema]"
```

Python API example:

```python
from pop import load_persona, validate_persona
from pop.projections import project_to_crewai, project_to_langchain

persona = load_persona(
    "examples/cross-runtime-persona-portability/personas/lawyer_persona.json"
)
validate_persona(persona)

langchain_view = project_to_langchain(persona)
crewai_view = project_to_crewai(persona)
```

## POP-Core Paper

Zhang, B. (2026). *POP-Core: Formal Semantics and Interoperability of Portable Persona Objects*. Zenodo. https://doi.org/10.5281/zenodo.18907957

## What POP is

POP defines a minimal object layer for packaging persona definitions in a portable and inspectable form. It focuses on persona object representation, plugin attachment entry points, separation from memory and permissions, and basic governance boundaries.

## What POP solves

POP provides a minimal shared structure for describing persona objects across systems. Its purpose is to keep persona definitions distinct from memory stores, capability grants, and application-specific orchestration logic.

## Scope

POP v0.1 covers:

- a minimal persona core
- optional memory hook declarations
- optional plugin manifest declarations
- explicit safety and governance boundaries
- simple draft version labeling

## Non-goals

POP is not:

- a full personality generation system
- a model training or fine-tuning method
- a robotics stack
- a digital immortality framework
- a universal cross-model persona injection method
- a task intent object format
- an action exchange object format
- a result exchange object format
- a substitute for permission, identity, or memory systems

## Minimal structure

A POP object is intentionally small. The reference structure in this repository includes:

- `schema_version` for draft compatibility
- `id`, `name`, and `description` for identity and positioning
- `traits`, `anchors`, and `behavior` for the persona core
- `memory_hooks` as references to separate memory subsystems
- `plugins` as declarative attachment entry points

The object does not embed long-term memory, permission grants, or execution policy.

## Relationship to adjacent work

POP complements adjacent work on persona steering, persona consistency, agent tooling, and agent security. It does not replace those areas. Its role is narrower: to define a portable persona object layer that other systems can interpret, constrain, or extend.

For external messaging and positioning copy, see [`docs/communication-kit.md`](docs/communication-kit.md).

## Repository structure

```text
.
├── .zenodo.json
├── CITATION.cff
├── LICENSE
├── README.md
├── adapters
│   ├── crewai
│   ├── langchain
│   ├── llamaindex
│   └── microsoft-agent-framework
├── docs
│   ├── README.md
│   ├── cite-pop.md
│   ├── communication-kit.md
│   ├── pop-adapter-model.md
│   ├── pop-ecosystem-roadmap.md
│   └── short-outreach-kit.md
├── examples
│   ├── cross-runtime-persona-portability
│   ├── caregiver.persona.json
│   ├── companion.persona.json
│   └── mentor.persona.json
├── schema
│   └── persona.schema.json
└── spec
    └── pop-0.1.md
```

## Status

This repository contains a positioning-first `v0.1.0-draft`. It is a draft protocol, not a stable standard, and not a guarantee of high-fidelity persona transfer across models or products.

For a forward-looking RFC-style core draft, see [`spec/POP-core.md`](spec/POP-core.md).
For the draft canonical JSON binding, see [`spec/POP-json-binding.md`](spec/POP-json-binding.md) and [`schema/pop.schema.json`](schema/pop.schema.json).
For minimal runtime integration patterns, see [`docs/interop.md`](docs/interop.md).

## CLI

The repository now includes a minimal reference CLI for POP:

```bash
python3 -m pip install -e .
pop validate examples/mentor.v1.json
pop project examples/mentor.v1.json --runtime prompt
pop migrate-pop01 examples/mentor.persona.json
```

### CLI registry / persona reference commands

The POP CLI prototype now supports persona-reference-based operations.

Examples:

```bash
pop resolve pop:marketing_manager_v1
pop validate-id pop:marketing_manager_v1
pop project-id pop:marketing_manager_v1 --runtime agent
```

This extends the CLI from file-based usage toward registry-based
persona resolution.

## End-to-end quickstart

This repository now supports a minimal end-to-end POP workflow based on
persona references.

### 1. Prepare environment

Create a virtual environment and install the minimal dependencies used
by the current prototype:

```bash
python -m venv .venv
source .venv/bin/activate
pip install pyyaml jsonschema
```

### 2. Inspect the local persona registry prototype

```bash
python example_registry.py
```

Expected output includes:

- available local persona files
- normalized persona IDs such as `marketing_manager_v1`
- resolution of `pop:marketing_manager_v1` to `personas/marketing_manager.json`

### 3. Resolve a persona reference

```bash
PYTHONPATH=src python -m pop_protocol.cli resolve pop:marketing_manager_v1
```

Example output:

```text
personas/marketing_manager.json
```

### 4. Validate a persona by reference

```bash
PYTHONPATH=src python -m pop_protocol.cli validate-id pop:marketing_manager_v1
```

Example output:

```json
{
  "valid": true,
  "path": "personas/marketing_manager.json"
}
```

### 5. Project a persona into an agent-oriented runtime view

```bash
PYTHONPATH=src python -m pop_protocol.cli project-id pop:marketing_manager_v1 --runtime agent
```

This returns a non-empty JSON projection that demonstrates a minimal
runtime-facing contract derived from a POP persona reference.

### Workflow summary

The current prototype now supports the following end-to-end flow:

```text
persona ref
→ registry resolve
→ schema validate
→ runtime projection
```

This quickstart reflects the current prototype stage of POP tooling and
is intended for early experimentation rather than production
deployment.

For a slightly more detailed walkthrough, see
[`docs/quickstart.md`](docs/quickstart.md).

For direct local execution without installation:

```bash
python3 cli/pop_cli.py validate examples/mentor.v1.json
```

## LangChain Integration

POP now includes a first runtime integration for LangChain:

```bash
python3 -m pip install -e ".[langchain]"
python3 examples/langchain_agent.py examples/mentor.v1.json --print-config
```

Middleware-oriented preview package:

```bash
python3 examples/langchain_middleware_demo.py --print-config
```

The installed package exposes `langchain_pop` as a middleware-oriented preview layer for LangChain agents. It injects the POP-derived system prompt, preserves persona identity in runtime state, and filters tools against POP boundaries.

An extraction-ready standalone package scaffold is available at [`integrations/langchain-pop`](integrations/langchain-pop).

If you have `OPENAI_API_KEY` configured, you can invoke a live LangChain agent:

```bash
python3 examples/langchain_agent.py examples/mentor.v1.json --model gpt-4.1-mini
python3 examples/langchain_middleware_demo.py --invoke --model gpt-4.1-mini
```

Package API:

```python
from pop_protocol.adapters.langchain import create_langchain_agent, pop_to_langchain_config
from langchain_pop.agent import create_pop_agent
from langchain_pop.middleware import POPMiddleware
```

## CI And Packaging

The repository includes a GitHub Actions workflow at [`.github/workflows/validate.yml`](.github/workflows/validate.yml) that:

- validates all JSON example objects with `pop validate`
- builds the Python distribution with `python -m build`

Typical local packaging commands:

```bash
python3 -m pip install -e .
python3 -m pip install build
python3 -m build
```

The repository includes dedicated TestPyPI and PyPI trusted publishing
workflows under [`.github/workflows/`](.github/workflows/), and package
publication now follows tagged release and smoke-validation discipline.

## FDO-facing Note

For FDO-related positioning, see [docs/fdo-relation-note.md](docs/fdo-relation-note.md).

## Architecture Navigation

- [Digital Biosphere Architecture](https://github.com/joy7758/digital-biosphere-architecture)
- [Persona Object Protocol](https://github.com/joy7758/persona-object-protocol)
- [Agent Intent Protocol](https://github.com/joy7758/agent-intent-protocol)
- [Token Governor](https://github.com/joy7758/token-governor)
- [MVK](https://github.com/joy7758/fdo-kernel-mvk)
- [ARO Audit](https://github.com/joy7758/aro-audit)
<!-- render-refresh: 20260311T205242Z -->
