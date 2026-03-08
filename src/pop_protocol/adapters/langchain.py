from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pop_protocol.core import load_pop, slugify


def _boundary_instruction(boundary_name: str, boundary_value: Any) -> str:
    if isinstance(boundary_value, bool):
        if boundary_value is False:
            return f"- `{boundary_name}`: do not claim authority in this area."
        return (
            f"- `{boundary_name}`: the persona object does not prohibit this area, "
            "but runtime policy still decides whether action is allowed."
        )

    decision = boundary_value["decision"]
    reason = boundary_value.get("reason", "")
    suffix = f" Reason: {reason}" if reason else ""

    if decision == "requires-review":
        return f"- `{boundary_name}`: require human or policy review before acting.{suffix}"
    if decision == "disallow":
        return f"- `{boundary_name}`: do not act as if authority is granted here.{suffix}"
    if decision == "out-of-scope":
        return f"- `{boundary_name}`: treat as outside the persona's scope.{suffix}"
    if decision == "allow":
        return (
            f"- `{boundary_name}`: this boundary is not restrictive by itself; "
            f"still rely on runtime policy.{suffix}"
        )
    return f"- `{boundary_name}`: boundary is unspecified; respond conservatively.{suffix}"


def build_langchain_system_prompt(
    source: str | dict[str, Any],
    *,
    extra_instructions: str | None = None,
) -> str:
    pop_object = load_pop(source)
    boundary_lines = [
        _boundary_instruction(name, value) for name, value in pop_object["boundaries"].items()
    ]
    provenance = pop_object["provenance"]
    provenance_bits = []
    if "author" in provenance:
        provenance_bits.append(f"author={provenance['author']}")
    if "issuer" in provenance:
        provenance_bits.append(f"issuer={provenance['issuer']}")
    provenance_bits.append(f"created={provenance['created']}")

    lines = [
        "You are operating under a Persona Object Protocol (POP) persona object.",
        f"Role: {pop_object['role']}",
        f"Traits: {', '.join(pop_object['traits'])}",
        f"Object id: {pop_object['id']}",
        f"Version: {pop_object['version']}",
        f"Status: {pop_object['status']}",
        f"Provenance: {', '.join(provenance_bits)}",
        "Persona boundaries:",
        *boundary_lines,
        "Honor these persona boundaries during reasoning and tool use.",
        "Do not treat persona boundaries as permission grants.",
        "If runtime policy and persona boundaries conflict, follow the stricter constraint.",
    ]
    if extra_instructions:
        lines.extend(["Additional runtime instructions:", extra_instructions.strip()])
    return "\n".join(lines)


@dataclass(frozen=True)
class LangChainPersonaConfig:
    system_prompt: str
    agent_name: str
    persona: str
    constraints: dict[str, Any]
    metadata: dict[str, Any]
    pop_object: dict[str, Any]

    def create_agent_kwargs(self) -> dict[str, Any]:
        return {
            "name": self.agent_name,
            "system_prompt": self.system_prompt,
        }


def pop_to_langchain_config(
    source: str | dict[str, Any],
    *,
    agent_name: str | None = None,
    extra_instructions: str | None = None,
) -> LangChainPersonaConfig:
    pop_object = load_pop(source)
    role_slug = slugify(pop_object["role"]).replace("-", "_")
    return LangChainPersonaConfig(
        system_prompt=build_langchain_system_prompt(
            pop_object,
            extra_instructions=extra_instructions,
        ),
        agent_name=agent_name or role_slug or "pop_agent",
        persona=pop_object["role"],
        constraints=pop_object["boundaries"],
        metadata={
            "pop_id": pop_object["id"],
            "pop_version": pop_object["version"],
            "pop_status": pop_object["status"],
            "pop_kind": pop_object["kind"],
        },
        pop_object=pop_object,
    )


def create_langchain_agent(
    source: str | dict[str, Any],
    *,
    model: Any,
    tools: list[Any] | None = None,
    extra_instructions: str | None = None,
    name: str | None = None,
    **kwargs: Any,
) -> Any:
    try:
        from langchain.agents import create_agent
    except ImportError as exc:
        raise ImportError(
            "LangChain is not installed. Install it with `pip install -e \".[langchain]\"`."
        ) from exc

    config = pop_to_langchain_config(
        source,
        agent_name=name,
        extra_instructions=extra_instructions,
    )
    return create_agent(
        model=model,
        tools=tools or [],
        **config.create_agent_kwargs(),
        **kwargs,
    )
