from __future__ import annotations

from pop.models import PersonaObject


def project_to_langchain(persona: PersonaObject) -> dict:
    """Return an experimental LangChain-facing projection of a POP persona."""

    return {
        "system_framing": persona.summary,
        "style_guidance": list(persona.communication_style),
        "response_policy_hints": list(persona.task_orientation),
        "guardrail_instructions": list(persona.boundaries),
        "output_format_hints": list(persona.preferred_outputs),
    }
