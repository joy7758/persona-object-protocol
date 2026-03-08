# POP Interoperability Notes

This document describes the minimum interoperability paths for POP objects.

## POP to Prompt Runtime

```text
POP object
  ->
pop project --runtime prompt
  ->
system prompt text
```

Example:

```bash
pop project examples/mentor.v1.json --runtime prompt
```

This path is the most portable but also the most lossy. Structured boundaries and provenance metadata may be flattened into text.

## POP to Application Runtime

```text
POP object
  ->
pop project --runtime app
  ->
application role model
```

Example:

```bash
pop project examples/mentor.v1.json --runtime app
```

This path preserves a structured role model that is suitable for application-layer configuration and UI binding.

## POP to Agent Runtime

```text
POP object
  ->
pop project --runtime agent
  ->
agent runtime contract
```

Example:

```bash
pop project examples/mentor.v1.json --runtime agent
```

This path preserves the most structure and is the preferred path for runtimes that can keep identity, boundaries, lifecycle state, and provenance in explicit fields.

## POP to LangChain Runtime

```text
POP object
  ->
langchain_pop middleware
  ->
LangChain create_agent(...)
  ->
CompiledStateGraph
```

Minimal config flow:

```bash
python3 -m pip install -e ".[langchain]"
python3 examples/langchain_middleware_demo.py --print-config
```

Live invocation flow:

```bash
python3 examples/langchain_middleware_demo.py --invoke --model gpt-4.1-mini
```

This path uses `POPMiddleware` to inject the POP-derived system prompt, preserve persona identity in runtime state, and filter or block tools according to POP boundaries.

## Legacy POP 0.1 Interop

Legacy `pop-0.1` objects are still accepted by the CLI, but they are treated as migration inputs rather than canonical v1.0 objects.

```bash
pop migrate-pop01 examples/mentor.persona.json
```

For runtime projection, the CLI will auto-migrate a `pop-0.1` object before projection:

```bash
pop project examples/mentor.persona.json --runtime app
```

## Recommended Interop Order

For new integrations, prefer this order:

1. POP v1.0 object
2. structured projection (`app` or `agent`)
3. prompt projection only when the target runtime cannot preserve structure
