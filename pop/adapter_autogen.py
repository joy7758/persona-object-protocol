from .loader import load_persona


def _system_message_from_persona(persona):
    system_parts = [f"You are a {persona.role}."]
    if persona.traits:
        system_parts.append(f"Traits: {', '.join(persona.traits)}.")
    if persona.goals:
        system_parts.append(f"Goals: {'; '.join(persona.goals)}.")
    if persona.style:
        system_parts.append(f"Communication style: {persona.style}.")
    if persona.memory_scope:
        system_parts.append(f"Memory scope: {persona.memory_scope}.")
    return " ".join(system_parts)


def persona_to_autogen_config(path, model="gpt-4o", tools=None):
    p = load_persona(path)
    resolved_tools = tools if tools is not None else p.tools

    return {
        "name": p.name,
        "system_message": _system_message_from_persona(p),
        "model": model,
        "tools": resolved_tools,
        "metadata": {
            "persona_id": p.persona_id,
            "role": p.role,
            "memory_scope": p.memory_scope,
        },
    }


def assistant_agent_from_persona(
    path,
    model_client=None,
    tools=None,
    model="gpt-4o",
    **kwargs,
):
    cfg = persona_to_autogen_config(path, model=model, tools=tools)

    try:
        from autogen_agentchat.agents import AssistantAgent
    except Exception:
        return {
            "status": "AUTOGEN_NOT_INSTALLED",
            "config": cfg,
        }

    if model_client is None:
        return {
            "status": "MODEL_CLIENT_REQUIRED",
            "config": cfg,
        }

    return AssistantAgent(
        name=cfg["name"],
        model_client=model_client,
        tools=cfg["tools"],
        system_message=cfg["system_message"],
        **kwargs,
    )


def agent_from_persona(path, model="gpt-4o", **kwargs):
    return {
        "status": "DEPRECATED_ALIAS",
        "message": (
            "Use assistant_agent_from_persona(...) with a model_client "
            "for AutoGen-aligned usage."
        ),
        "config": persona_to_autogen_config(path, model=model),
        "kwargs": kwargs,
    }
