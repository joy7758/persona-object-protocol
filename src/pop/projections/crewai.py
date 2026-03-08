from __future__ import annotations

from pop.models import PersonaObject


def project_to_crewai(persona: PersonaObject) -> dict:
    """Return an experimental CrewAI-facing projection of a POP persona."""

    backstory_parts = [*persona.traits, *persona.communication_style]
    return {
        "role": persona.summary,
        "goal": list(persona.task_orientation),
        "backstory": backstory_parts,
        "behavioral_constraints": list(persona.boundaries),
        "output_expectations": list(persona.preferred_outputs),
    }
