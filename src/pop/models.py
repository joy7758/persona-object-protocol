from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, dict):
        collected: list[str] = []
        for item in value.values():
            if isinstance(item, list):
                collected.extend(str(part).strip() for part in item if str(part).strip())
            else:
                text = str(item).strip()
                if text:
                    collected.append(text)
        return collected
    text = str(value).strip()
    return [text] if text else []


@dataclass
class PersonaObject:
    id: str = ""
    version: str = ""
    name: str = ""
    summary: str = ""
    traits: list[str] = field(default_factory=list)
    communication_style: list[str] = field(default_factory=list)
    task_orientation: list[str] = field(default_factory=list)
    boundaries: list[str] = field(default_factory=list)
    preferred_outputs: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PersonaObject:
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        return cls(
            id=str(data.get("id", "")).strip(),
            version=str(data.get("version", "")).strip(),
            name=str(data.get("name", "")).strip(),
            summary=str(data.get("summary", "")).strip(),
            traits=_string_list(data.get("traits")),
            communication_style=_string_list(data.get("communication_style")),
            task_orientation=_string_list(data.get("task_orientation")),
            boundaries=_string_list(data.get("boundaries")),
            preferred_outputs=_string_list(data.get("preferred_outputs")),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "summary": self.summary,
            "traits": list(self.traits),
            "communication_style": list(self.communication_style),
            "task_orientation": list(self.task_orientation),
            "boundaries": list(self.boundaries),
            "preferred_outputs": list(self.preferred_outputs),
            "metadata": dict(self.metadata),
        }
