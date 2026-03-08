from __future__ import annotations

from pop.adapters import CrewAIAdapter
from pop.models import PersonaObject


def bind_crewai_agent_kwargs(persona: PersonaObject) -> dict:
    """Return an early-preview CrewAI agent kwargs scaffold."""

    projection = CrewAIAdapter().adapt(persona)
    return {
        "role": projection["role"],
        "goal": "\n".join(projection["goal"]),
        "backstory": "\n".join(projection["backstory"]),
        "behavioral_constraints": list(projection["behavioral_constraints"]),
        "output_expectations": list(projection["output_expectations"]),
    }


def create_crewai_agent_from_persona(
    persona: PersonaObject, **kwargs
) -> dict:
    """Return a runtime-facing CrewAI agent scaffold, not an official type."""

    scaffold = bind_crewai_agent_kwargs(persona)
    passthrough = dict(kwargs)
    if "tools" in passthrough:
        passthrough["tools"] = list(passthrough["tools"])
    scaffold.update(passthrough)
    scaffold["adapter"] = "crewai"
    scaffold["persona_id"] = persona.id
    return scaffold
