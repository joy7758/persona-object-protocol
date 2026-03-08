from __future__ import annotations

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


def create_langchain_agent_kwargs(
    persona: PersonaObject,
    *,
    tools: list | None = None,
    system_prompt_prefix: str | None = None,
    model: str | None = None,
) -> dict:
    """Return an early-preview create_agent helper, not an official LangChain type."""

    prompt = bind_langchain_prompt(persona)
    if system_prompt_prefix:
        prompt = f"{system_prompt_prefix.strip()}\n\n{prompt}"

    agent_kwargs = {
        "system_prompt": prompt,
        "context": bind_langchain_context(persona),
        "middleware": bind_langchain_middleware(persona),
        "tools": list(tools or []),
    }
    if model is not None:
        agent_kwargs["model"] = model
    return agent_kwargs


def create_langchain_execution_scaffold(
    persona: PersonaObject,
    *,
    tools: list | None = None,
    model: str | None = None,
) -> dict:
    """Return an early-preview execution scaffold for LangChain consumption."""

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
        "middleware": create_langchain_middleware_scaffold(persona),
    }


def create_langchain_middleware_scaffold(
    persona: PersonaObject,
) -> list[dict]:
    """Return an early-preview middleware list, not an official LangChain type."""

    return [
        {
            "name": "pop_persona_middleware",
            "binding": bind_langchain_middleware(persona),
        }
    ]


def build_langchain_agent_input(
    persona: PersonaObject,
    *,
    tools: list | None = None,
    model: str | None = None,
) -> dict:
    """Return a lightweight LangChain-facing input bundle for local scaffolds."""

    return create_langchain_execution_scaffold(
        persona,
        tools=tools,
        model=model,
    )
