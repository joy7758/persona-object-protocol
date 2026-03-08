from __future__ import annotations

from pop.adapters.base import BasePersonaAdapter
from pop.models import PersonaObject


class LangChainAdapter(BasePersonaAdapter):
    """Experimental LangChain-facing adapter for canonical POP persona objects."""

    adapter_name = "langchain"

    def adapt(self, persona: PersonaObject) -> dict:
        return {
            "system_framing": persona.summary,
            "style_guidance": list(persona.communication_style),
            "response_policy_hints": list(persona.task_orientation),
            "guardrail_instructions": list(persona.boundaries),
            "output_format_hints": list(persona.preferred_outputs),
        }
