import json
from pathlib import Path

from .loader import load_persona


def _goal_from_persona(persona):
    if persona.goals:
        return "; ".join(persona.goals)
    return f"Act effectively as {persona.role}"


def _backstory_from_persona(persona):
    backstory_bits = [persona.name]
    if persona.traits:
        backstory_bits.append(f"Traits: {', '.join(persona.traits)}")
    if persona.style:
        backstory_bits.append(f"Communication style: {persona.style}")
    if persona.memory_scope:
        backstory_bits.append(f"Memory scope: {persona.memory_scope}")
    return ". ".join(backstory_bits)


def _yaml_quote(value):
    return json.dumps(value, ensure_ascii=False)


def _render_crewai_agent_yaml_lines(agent_name, config):
    lines = [
        f"{agent_name}:",
        f"  role: {_yaml_quote(config['role'])}",
        f"  goal: {_yaml_quote(config['goal'])}",
        f"  backstory: {_yaml_quote(config['backstory'])}",
    ]

    if config.get("tools"):
        lines.append("  tools:")
        for tool in config["tools"]:
            lines.append(f"    - {_yaml_quote(tool)}")

    return lines


def agent_from_persona(path, llm, tools=None, **agent_kwargs):
    try:
        from crewai import Agent
    except Exception as e:
        raise RuntimeError(
            "CrewAI is not installed. Please install it first, e.g. `pip install crewai`."
        ) from e

    p = load_persona(path)

    resolved_tools = tools if tools is not None else p.tools

    agent = Agent(
        role=p.role,
        goal=_goal_from_persona(p),
        backstory=_backstory_from_persona(p),
        tools=resolved_tools,
        llm=llm,
        **agent_kwargs,
    )

    return agent


def persona_to_crewai_config(path):
    p = load_persona(path)
    return {
        "role": p.role,
        "goal": _goal_from_persona(p),
        "backstory": _backstory_from_persona(p),
        "tools": p.tools,
    }


def export_crewai_agent_yaml(path, output_path, agent_name="agent"):
    config = persona_to_crewai_config(path)
    output_path = Path(output_path)
    lines = _render_crewai_agent_yaml_lines(agent_name, config)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(output_path)


def export_crewai_agents_yaml(persona_map, output_path):
    output_path = Path(output_path)
    blocks = []

    for agent_key, persona_path in persona_map.items():
        config = persona_to_crewai_config(persona_path)
        blocks.append("\n".join(_render_crewai_agent_yaml_lines(agent_key, config)))

    output_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return str(output_path)
