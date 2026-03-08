from __future__ import annotations

from importlib import import_module

from pop.adapters import LangChainAdapter
from pop.models import PersonaObject


def bind_langchain_prompt(persona: PersonaObject) -> str:
    """Return an early-preview LangChain prompt scaffold for a POP persona."""

    sections = [
        f"Persona name: {persona.name}",
        f"Summary: {persona.summary}",
    ]
    if persona.communication_style:
        sections.append(
            "Style guidance: " + "; ".join(persona.communication_style)
        )
    if persona.task_orientation:
        sections.append(
            "Task orientation: " + "; ".join(persona.task_orientation)
        )
    if persona.boundaries:
        sections.append("Boundaries: " + "; ".join(persona.boundaries))
    if persona.preferred_outputs:
        sections.append(
            "Preferred outputs: " + "; ".join(persona.preferred_outputs)
        )
    return "\n".join(sections)


def bind_langchain_context(persona: PersonaObject) -> dict:
    """Return an early-preview context binding, not an official LangChain type."""

    projection = LangChainAdapter().adapt(persona)
    return {
        "persona_id": persona.id,
        "persona_name": persona.name,
        "persona_summary": projection["system_framing"],
        "style_guidance": list(projection["style_guidance"]),
        "response_policy_hints": list(projection["response_policy_hints"]),
        "guardrail_instructions": list(projection["guardrail_instructions"]),
        "output_format_hints": list(projection["output_format_hints"]),
        "metadata": dict(persona.metadata),
    }


def bind_langchain_middleware(persona: PersonaObject) -> dict:
    """Return an early-preview middleware binding scaffold for LangChain."""

    projection = LangChainAdapter().adapt(persona)
    return {
        "adapter": "langchain",
        "persona_id": persona.id,
        "system_framing": projection["system_framing"],
        "style_guidance": list(projection["style_guidance"]),
        "response_policy_hints": list(projection["response_policy_hints"]),
        "guardrail_instructions": list(projection["guardrail_instructions"]),
        "output_format_hints": list(projection["output_format_hints"]),
    }


def create_langchain_context_bundle(persona: PersonaObject) -> dict:
    """Return an early-preview runtime-context scaffold, not a create_agent parameter."""

    return {
        "kind": "runtime_context",
        "runtime": "langchain",
        "persona": bind_langchain_context(persona),
    }


def create_langchain_middleware_bundle(
    persona: PersonaObject,
) -> list[dict]:
    """Return an early-preview middleware-facing helper bundle, not an official LangChain type."""

    return [
        {
            "name": "pop_persona_middleware",
            "binding": bind_langchain_middleware(persona),
        }
    ]


def create_langchain_create_agent_kwargs(
    persona: PersonaObject,
    *,
    tools: list | None = None,
    model: str | None = None,
    system_prompt_prefix: str | None = None,
) -> dict:
    """Return an early-preview helper aligned with LangChain v1 create_agent parameter semantics."""

    prompt = bind_langchain_prompt(persona)
    if system_prompt_prefix:
        prompt = f"{system_prompt_prefix.strip()}\n\n{prompt}"

    agent_kwargs = {
        "system_prompt": prompt,
        "tools": list(tools or []),
    }
    if model is not None:
        agent_kwargs["model"] = model
    return agent_kwargs


def create_langchain_execution_bundle(
    persona: PersonaObject,
    *,
    tools: list | None = None,
    model: str | None = None,
    system_prompt_prefix: str | None = None,
) -> dict:
    """Return the main early-preview LangChain execution contract surface."""

    return {
        "runtime": "langchain",
        "target": "create_agent",
        "persona_id": persona.id,
        "create_agent_kwargs": create_langchain_create_agent_kwargs(
            persona,
            tools=tools,
            model=model,
            system_prompt_prefix=system_prompt_prefix,
        ),
        "context_bundle": create_langchain_context_bundle(persona),
        "middleware_bundle": create_langchain_middleware_bundle(persona),
        "metadata": {
            "entrypoint": "create_langchain_execution_bundle",
            "surface": "execution_contract",
            "compatibility_helpers": [
                "create_langchain_agent_kwargs",
                "create_langchain_execution_scaffold",
                "create_langchain_middleware_scaffold",
            ],
        },
    }


def create_langchain_agent_kwargs(
    persona: PersonaObject,
    *,
    tools: list | None = None,
    system_prompt_prefix: str | None = None,
    model: str | None = None,
) -> dict:
    """Return an early-preview compatibility helper, not the main contract surface."""

    agent_kwargs = dict(
        create_langchain_create_agent_kwargs(
            persona,
            tools=tools,
            model=model,
            system_prompt_prefix=system_prompt_prefix,
        )
    )
    agent_kwargs["context"] = bind_langchain_context(persona)
    agent_kwargs["middleware"] = bind_langchain_middleware(persona)
    return agent_kwargs


def create_langchain_execution_scaffold(
    persona: PersonaObject,
    *,
    tools: list | None = None,
    model: str | None = None,
) -> dict:
    """Return an early-preview compatibility helper wrapping the main execution bundle."""

    bundle = create_langchain_execution_bundle(
        persona,
        tools=tools,
        model=model,
    )
    return {
        "runtime": "langchain",
        "adapter": "langchain",
        "persona_id": persona.id,
        "agent_kwargs": create_langchain_agent_kwargs(
            persona,
            tools=tools,
            model=model,
        ),
        "context": bind_langchain_context(persona),
        "middleware": create_langchain_middleware_bundle(persona),
        "bundle": bundle,
    }


def create_langchain_middleware_scaffold(
    persona: PersonaObject,
) -> list[dict]:
    """Return an early-preview compatibility helper wrapping the middleware bundle."""

    return create_langchain_middleware_bundle(persona)


def build_langchain_agent_input(
    persona: PersonaObject,
    *,
    tools: list | None = None,
    model: str | None = None,
) -> dict:
    """Return an early-preview compatibility helper for local LangChain scaffolds."""

    return create_langchain_execution_scaffold(
        persona,
        tools=tools,
        model=model,
    )


def maybe_build_langchain_agent_spec(
    persona: PersonaObject,
    *,
    tools: list | None = None,
    model: str | None = None,
    system_prompt_prefix: str | None = None,
) -> dict:
    """Return an early-preview dependency-aware LangChain helper spec without live execution."""

    try:
        langchain_module = import_module("langchain")
    except ImportError:
        return {
            "langchain_available": False,
            "runtime": "langchain",
            "target": "create_agent",
            "kind": "langchain_execution_scaffold",
            "execution_bundle": create_langchain_execution_bundle(
                persona,
                tools=tools,
                model=model,
                system_prompt_prefix=system_prompt_prefix,
            ),
            "note": "Install the optional langchain extra for dependency-aware execution helpers.",
        }

    return {
        "langchain_available": True,
        "langchain_version": getattr(langchain_module, "__version__", "unknown"),
        "runtime": "langchain",
        "target": "create_agent",
        "kind": "langchain_execution_helper_spec",
        "create_agent_kwargs": create_langchain_create_agent_kwargs(
            persona,
            tools=tools,
            model=model,
            system_prompt_prefix=system_prompt_prefix,
        ),
        "context_bundle": create_langchain_context_bundle(persona),
        "middleware_bundle": create_langchain_middleware_bundle(persona),
    }
