from __future__ import annotations

from demos.task_registry import PersonaDefinition


BUILTIN_PERSONAS = (
    PersonaDefinition(
        persona_id="design_persona",
        file_path="personas/design_persona.json",
    ),
    PersonaDefinition(
        persona_id="research_persona",
        file_path="personas/researcher_persona.json",
    ),
    PersonaDefinition(
        persona_id="marketing_persona",
        file_path="personas/marketing_persona.json",
    ),
)
