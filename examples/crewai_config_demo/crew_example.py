"""
CrewAI recommended YAML configuration path demo.

This example shows how POP-exported agent YAML could be consumed
through a CrewAI-style config-based workflow.

It is intentionally conservative:
- if PyYAML is not installed, it prints guidance and exits cleanly
- if crewai is not installed, it prints guidance and exits cleanly
- if installed, it attempts to construct agents from config entries
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


def main():
    config = load_agents_config()
    if config is None:
        return

    print("CONFIG_LOADED")
    print(config)

    try:
        from crewai import Agent
    except Exception:
        print("CREWAI_NOT_INSTALLED")
        print("Install with: pip install crewai")
        return

    built = {}
    for key, value in config.items():
        built[key] = Agent(
            role=value["role"],
            goal=value["goal"],
            backstory=value["backstory"],
            tools=value.get("tools", []),
            llm="gpt-4o",
        )

    print("AGENTS_BUILT")
    print({k: type(v).__name__ for k, v in built.items()})


if __name__ == "__main__":
    main()
