from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pop import load_persona
from pop.integrations.crewai import create_crewai_agent_kwargs


SHARED_TASK_BRIEF = "Plan the first POP landing page and launch outline"
DEMO_REGISTRY = {
    "designer": {
        "persona_ref": "pop:designer_v1",
        "source_path": ROOT / "examples" / "pop_team_demo" / "personas" / "designer.json",
    },
    "engineer": {
        "persona_ref": "pop:engineer_v1",
        "source_path": ROOT / "examples" / "pop_team_demo" / "personas" / "engineer.json",
    },
    "marketing_manager": {
        "persona_ref": "pop:marketing_manager_v1",
        "source_path": ROOT / "examples" / "pop_team_demo" / "personas" / "marketing_manager.json",
    },
}


def build_demo_payload() -> dict[str, object]:
    team = []
    for role_key, entry in DEMO_REGISTRY.items():
        source_path = Path(entry["source_path"])
        persona = load_persona(source_path)
        team.append(
            {
                "role_key": role_key,
                "persona_ref": entry["persona_ref"],
                "source_path": str(source_path.relative_to(ROOT)),
                "crewai_agent_kwargs": create_crewai_agent_kwargs(
                    persona,
                    verbose=False,
                ),
                "shared_task_brief": SHARED_TASK_BRIEF,
            }
        )

    return {
        "shared_task_brief": SHARED_TASK_BRIEF,
        "team": team,
    }


def main() -> None:
    print(json.dumps(build_demo_payload(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
