# LangChain Minimal Adoption Path

## Purpose

This quickstart shows the smallest practical path for evaluating POP
against LangChain-facing execution helpers without introducing live
model calls or runtime dependencies beyond the optional `langchain`
extra.

## Install

```bash
pip install "pop-persona[schema,langchain]"
```

## Minimal Persona Input

The quickest evaluation path starts from a valid POP persona object.
The canonical schema baseline remains `v0.1.0`, and the fixture corpus
already contains a suitable minimal example:

- `fixtures/valid/lawyer_persona.json`

## Minimal LangChain Adoption Path

`create_langchain_execution_bundle(...)` is the primary LangChain-facing
entry point in this release line. It returns one contract surface with
three layers:

- `create_agent_kwargs`
- `context_bundle`
- `middleware_bundle`

Minimal example:

```bash
python examples/integrations/langchain_minimal_20_lines.py
```

## Installed-Package Smoke Path

The installed-package smoke path is intended to reduce first-adoption
friction:

```bash
python examples/integrations/langchain_installed_smoke_minimal.py
```

This path checks both the main execution bundle and the optional
dependency-aware spec returned by
`maybe_build_langchain_agent_spec(...)`.

## Compatibility Notes

Compatibility helpers remain available for backward compatibility, but
they are not the primary path for first evaluation. The recommended
starting point is:

- `create_langchain_execution_bundle(...)`

## Non-Goals

- no real model execution
- no network access
- no claim of official LangChain runtime integration
- no change to the canonical schema baseline
