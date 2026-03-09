"""
CrewAI CrewBase-style demo for POP-exported agents.yaml.

This demo mirrors CrewAI's recommended YAML path:
- config/agents.yaml
- Python methods whose names match YAML keys

It is intentionally conservative:
- if PyYAML is not installed, it prints guidance and exits cleanly
- if crewai is not installed, it prints guidance and returns config stubs
- if installed, it attempts to construct Agent objects from config entries
"""

from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config" / "agents.yaml"


def load_agents_config():
    try:
        import yaml
    except Exception:
        print("PY_YAML_NOT_INSTALLED")
        print("Install with: pip install pyyaml")
        return None

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class POPCrewDemo:
    def __init__(self, agents_config=None):
        self.agents_config = agents_config if agents_config is not None else load_agents_config()

    def marketing_manager(self):
        return self._build_agent("marketing_manager")

    def engineer(self):
        return self._build_agent("engineer")

    def designer(self):
        return self._build_agent("designer")

    def _build_agent(self, key):
        if self.agents_config is None:
            return {"agent_key": key, "status": "PY_YAML_NOT_INSTALLED"}

        cfg = self.agents_config[key]

        try:
            from crewai import Agent
        except Exception:
            return {
                "agent_key": key,
                "config": cfg,
                "status": "CREWAI_NOT_INSTALLED",
            }

        return Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            tools=cfg.get("tools", []),
            llm="gpt-4o",
        )


def main():
    demo = POPCrewDemo()

    if demo.agents_config is None:
        return

    print("CONFIG_KEYS")
    print(list(demo.agents_config.keys()))

    for key in ["marketing_manager", "engineer", "designer"]:
        result = getattr(demo, key)()
        print(f"AGENT_{key.upper()}")
        print(result)


if __name__ == "__main__":
    main()
