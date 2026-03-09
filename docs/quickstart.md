# POP Quickstart

This quickstart shows the shortest working path through the current
Persona Object Protocol (POP) prototype.

## Goal

Run a minimal end-to-end workflow using a persona reference:

```text
pop:marketing_manager_v1
```

The current prototype supports:

```text
persona ref
→ registry resolve
→ schema validate
→ runtime projection
```

## Prerequisites

Use Python 3 and install the minimal dependencies required by the
current repository state:

```bash
python -m venv .venv
source .venv/bin/activate
pip install pyyaml jsonschema
```

## Step 1: Inspect local personas

Run:

```bash
python example_registry.py
```

This shows:

- local persona files under `personas/`
- normalized persona IDs
- a working example of POP persona reference resolution

## Step 2: Resolve a persona reference

Run:

```bash
PYTHONPATH=src python -m pop_protocol.cli resolve pop:marketing_manager_v1
```

Expected result:

```text
personas/marketing_manager.json
```

## Step 3: Validate by persona reference

Run:

```bash
PYTHONPATH=src python -m pop_protocol.cli validate-id pop:marketing_manager_v1
```

Expected result:

```json
{
  "valid": true,
  "path": "personas/marketing_manager.json"
}
```

## Step 4: Project into runtime form

Run:

```bash
PYTHONPATH=src python -m pop_protocol.cli project-id pop:marketing_manager_v1 --runtime agent
```

Expected result:

A non-empty JSON object that represents an agent-oriented projection
derived from the referenced persona.

## Interpretation

This prototype does not yet provide a remote registry or a stable
network URI layer.

Instead, it demonstrates a local tooling path in which:

- persona references can be normalized
- local registry entries can be resolved
- schema validation can be performed by reference
- runtime-oriented projection can be generated from the same reference

## Current scope

This quickstart reflects the current prototype stage of POP:

- local registry / SDK prototype
- early persona ID convention
- CLI persona-reference commands
- runtime-facing projection flow

For broader protocol details, see the specification and schema
documents in this repository.
