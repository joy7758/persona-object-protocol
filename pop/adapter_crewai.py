from .loader import load_persona


def agent_from_persona(path, llm, tools=None, **agent_kwargs):
    try:
        from crewai import Agent
    except Exception as e:
        raise RuntimeError(
            "CrewAI is not installed. Please install it first, e.g. `pip install crewai`."
        ) from e

    p = load_persona(path)

    resolved_tools = tools if tools is not None else p.tools

    backstory_bits = [f"{p.name}"]
    if p.traits:
        backstory_bits.append(f"Traits: {', '.join(p.traits)}")
    if p.style:
        backstory_bits.append(f"Communication style: {p.style}")
    if p.memory_scope:
        backstory_bits.append(f"Memory scope: {p.memory_scope}")

    backstory = ". ".join(backstory_bits)

    agent = Agent(
        role=p.role,
        goal="; ".join(p.goals) if p.goals else f"Act effectively as {p.role}",
        backstory=backstory,
        tools=resolved_tools,
        llm=llm,
        **agent_kwargs,
    )

    return agent
