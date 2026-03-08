from __future__ import annotations

from pop.adapters import CrewAIAdapter
from pop.models import PersonaObject


def bind_crewai_agent_kwargs(persona: PersonaObject) -> dict:
    """Return an early-preview CrewAI agent kwargs scaffold."""

    projection = CrewAIAdapter().adapt(persona)
    return {
        "role": projection["role"],
        "goal": "\n".join(projection["goal"]),
        "backstory": "\n".join(projection["backstory"]),
        "behavioral_constraints": list(projection["behavioral_constraints"]),
        "output_expectations": list(projection["output_expectations"]),
    }


def create_crewai_agent_kwargs(
    persona: PersonaObject,
    *,
    tools: list | None = None,
    llm: object | None = None,
    verbose: bool | None = None,
) -> dict:
    """Return an early-preview Agent(...) helper, not an official CrewAI type."""

    agent_kwargs = bind_crewai_agent_kwargs(persona)
    agent_kwargs["tools"] = list(tools or [])
    if llm is not None:
        agent_kwargs["llm"] = llm
    if verbose is not None:
        agent_kwargs["verbose"] = verbose
    return agent_kwargs


def create_crewai_execution_scaffold(
    persona: PersonaObject,
    *,
    tools: list | None = None,
    llm: object | None = None,
    verbose: bool | None = None,
) -> dict:
    """Return an early-preview execution scaffold for CrewAI consumption."""

    return {
        "runtime": "crewai",
        "adapter": "crewai",
        "persona_id": persona.id,
        "agent_kwargs": create_crewai_agent_kwargs(
            persona,
            tools=tools,
            llm=llm,
            verbose=verbose,
        ),
    }


def create_crewai_agent_from_persona(
    persona: PersonaObject, **kwargs
) -> dict:
    """Return a runtime-facing CrewAI agent scaffold, not an official type."""

    scaffold = create_crewai_agent_kwargs(persona, **kwargs)
    scaffold["adapter"] = "crewai"
    scaffold["persona_id"] = persona.id
    return scaffold


def build_crewai_agent_spec(
    persona: PersonaObject,
    *,
    tools: list | None = None,
    llm: object | None = None,
    verbose: bool | None = None,
) -> dict:
    """Return a lightweight CrewAI-facing spec bundle for local scaffolds."""

    return create_crewai_execution_scaffold(
        persona,
        tools=tools,
        llm=llm,
        verbose=verbose,
    )
