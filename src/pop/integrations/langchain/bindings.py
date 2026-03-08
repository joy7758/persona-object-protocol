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
