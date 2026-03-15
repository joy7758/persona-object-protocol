import json
from pathlib import Path


PERSONA_PATH = Path(__file__).resolve().parent / "personas" / "design_persona.json"


def load_persona(persona_path: Path) -> dict:
    with persona_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def print_persona(persona: dict) -> None:
    print(f"Name: {persona['name']}")
    print(f"Role: {persona['role']}")
    print(f"Skills: {', '.join(persona['skills'])}")


if __name__ == "__main__":
    print_persona(load_persona(PERSONA_PATH))
