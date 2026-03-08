from __future__ import annotations

from pop.adapters.base import BasePersonaAdapter
from pop.models import PersonaObject


class CrewAIAdapter(BasePersonaAdapter):
    """Experimental CrewAI-facing adapter for canonical POP persona objects."""

    adapter_name = "crewai"

    def adapt(self, persona: PersonaObject) -> dict:
        return {
            "role": persona.summary,
            "goal": list(persona.task_orientation),
            "backstory": [*persona.traits, *persona.communication_style],
            "behavioral_constraints": list(persona.boundaries),
            "output_expectations": list(persona.preferred_outputs),
        }
