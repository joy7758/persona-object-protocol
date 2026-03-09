import json
from pathlib import Path


REQUIRED_FIELDS = ["persona_id", "name", "role"]


class Persona:
    def __init__(self, data: dict):
        self.persona_id = data.get("persona_id")
        self.name = data.get("name")
        self.role = data.get("role")
        self.traits = data.get("traits", [])
        self.goals = data.get("goals", [])
        self.tools = data.get("tools", [])
        self.style = data.get("communication_style")
        self.memory_scope = data.get("memory_scope")

    def __repr__(self) -> str:
        return (
            f"Persona("
            f"persona_id={self.persona_id!r}, "
            f"name={self.name!r}, "
            f"role={self.role!r}, "
            f"traits={self.traits!r}, "
            f"goals={self.goals!r}, "
            f"tools={self.tools!r})"
        )


def load_persona(path: str | Path) -> Persona:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
    if missing:
        raise ValueError(f"Missing required persona fields: {', '.join(missing)}")

    return Persona(data)


def validate_persona(path):
    try:
        load_persona(path)
        return {"valid": True, "path": str(path)}
    except Exception as e:
        return {"valid": False, "path": str(path), "error": str(e)}
