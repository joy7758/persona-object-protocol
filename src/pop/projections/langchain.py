from __future__ import annotations

from pop.adapters import LangChainAdapter
from pop.models import PersonaObject


def project_to_langchain(persona: PersonaObject) -> dict:
    """Return an experimental LangChain-facing projection of a POP persona."""

    return LangChainAdapter().adapt(persona)
