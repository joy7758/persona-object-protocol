> **Maintenance notice**
>
> This repository is no longer the primary maintenance entry for the Agent Evidence / Operation Accountability Profile（智能体执行证据与操作问责配置文件）mainline. It is retained for migration review or historical reference. This change does not delete or archive the repository. See `MIGRATED_TO.md` for the current migration target and review status.

<!-- language-switch:start -->
[English](./README.md) | [中文](./README.zh-CN.md)
<!-- language-switch:end -->

# langchain-pop

Thin adapter and compatibility wrapper for [persona-object-protocol](https://github.com/joy7758/persona-object-protocol).

## Role

`langchain-pop` preserves a standalone packaging surface for LangChain users who want a minimal POP integration entrypoint. It exists to expose integration glue and migration continuity, not to redefine the Persona Object Protocol itself.

## Canonical home

The canonical implementation now lives in `persona-object-protocol`, under its POP integration surface and examples:

- `persona-object-protocol/integrations/langchain-pop`
- `persona-object-protocol/src/pop/integrations/langchain`

## Not this repo

- not the canonical persona protocol implementation
- not the architecture hub
- not the benchmark suite
- not the governance or audit layer

## Minimal usage

```bash
pip install langchain-pop
python examples/langchain_middleware_demo.py --print-config
```

```python
from langchain_openai import ChatOpenAI

from langchain_pop.agent import create_pop_agent

agent = create_pop_agent(
    pop_source="tests/fixtures/mentor.v1.json",
    model=ChatOpenAI(model="gpt-4o", temperature=0.0),
    tools=[],
)
```

For current protocol context, schema evolution, and integration guidance, start from `persona-object-protocol` and treat this repo as a compatibility wrapper.

## Status

- deprecated standalone wrapper
- canonical home is `persona-object-protocol`
- kept for packaging continuity and thin integration examples

## Notes

- The standalone package remains installable for now.
- Protocol semantics, schema, and canonical examples live in `persona-object-protocol`.
- Future consolidation may fold this wrapper completely into the parent repo.
