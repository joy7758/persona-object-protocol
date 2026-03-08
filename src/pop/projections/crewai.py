from __future__ import annotations

from pop.adapters import CrewAIAdapter
from pop.models import PersonaObject


def project_to_crewai(persona: PersonaObject) -> dict:
    """Return an experimental CrewAI-facing projection of a POP persona."""

    return CrewAIAdapter().adapt(persona)
