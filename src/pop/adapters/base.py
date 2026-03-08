from __future__ import annotations

from abc import ABC, abstractmethod

from pop.models import PersonaObject


class BasePersonaAdapter(ABC):
    """Early-preview adapter interface for runtime-facing persona bindings."""

    adapter_name = "base"

    @abstractmethod
    def adapt(self, persona: PersonaObject) -> dict:
        """Return a runtime-facing projection without mutating the persona."""
