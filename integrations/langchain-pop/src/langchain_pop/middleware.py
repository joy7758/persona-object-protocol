from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import SystemMessage, ToolMessage

from langchain_pop._pop_compat import build_langchain_system_prompt, load_pop, slugify


@dataclass(frozen=True)
class ToolBoundaryResult:
    allowed: bool
    boundary_key: str | None = None
    decision: str | None = None
    reason: str | None = None


def _normalize_tool_name(name: str) -> str:
    return slugify(name).replace("-", "_")


def _tool_targets(boundary_key: str, boundary_value: Any) -> list[str]:
    targets: list[str] = []
    for prefix in ("tool.", "tool:", "tool/"):
        if boundary_key.startswith(prefix):
            targets.append(boundary_key[len(prefix) :])
            break
    if boundary_key.startswith("tool_"):
        targets.append(boundary_key[len("tool_") :])

    if isinstance(boundary_value, dict):
        for scope in boundary_value.get("scope", []):
            if scope == "tool:*":
                targets.append("*")
            elif scope.startswith("tool:"):
                targets.append(scope[len("tool:") :])
            elif scope.startswith("tool/"):
                targets.append(scope[len("tool/") :])
    return targets


def _boundary_blocks_tool(boundary_value: Any) -> bool:
    if isinstance(boundary_value, bool):
        return boundary_value is False
    return boundary_value.get("decision") in {"disallow", "out-of-scope", "requires-review"}


def _tool_name(tool: Any) -> str:
    if hasattr(tool, "name"):
        return str(tool.name)
    if hasattr(tool, "__name__"):
        return str(tool.__name__)
    if isinstance(tool, dict):
        if "name" in tool:
            return str(tool["name"])
        if "function" in tool and isinstance(tool["function"], dict):
            if "name" in tool["function"]:
                return str(tool["function"]["name"])
    raise ValueError(f"Unable to determine tool name from {tool!r}")


def _system_message_text(system_message: Any) -> str:
    if system_message is None:
        return ""
    content = getattr(system_message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(system_message, str):
        return system_message
    return str(system_message)


class POPMiddleware(AgentMiddleware[Any, Any]):
    def __init__(
        self,
        source: str | dict[str, Any],
        *,
        extra_instructions: str | None = None,
        state_key: str = "pop_persona",
    ) -> None:
        self.pop_object = load_pop(source)
        self.system_prompt = build_langchain_system_prompt(
            self.pop_object,
            extra_instructions=extra_instructions,
        )
        self.state_key = state_key

    def persona_state(self) -> dict[str, Any]:
        return {
            "id": self.pop_object["id"],
            "version": self.pop_object["version"],
            "status": self.pop_object["status"],
            "role": self.pop_object["role"],
            "kind": self.pop_object["kind"],
            "boundaries": self.pop_object["boundaries"],
        }

    def tool_boundary_result(self, tool_name: str) -> ToolBoundaryResult:
        normalized_tool = _normalize_tool_name(tool_name)
        for boundary_key, boundary_value in self.pop_object["boundaries"].items():
            targets = _tool_targets(boundary_key, boundary_value)
            if not targets:
                continue

            normalized_targets = [_normalize_tool_name(target) for target in targets if target != "*"]
            wildcard = "*" in targets
            if not wildcard and normalized_tool not in normalized_targets:
                continue

            if _boundary_blocks_tool(boundary_value):
                reason = None
                decision = "disallow" if isinstance(boundary_value, bool) else boundary_value.get("decision")
                if isinstance(boundary_value, dict):
                    reason = boundary_value.get("reason")
                return ToolBoundaryResult(
                    allowed=False,
                    boundary_key=boundary_key,
                    decision=decision,
                    reason=reason,
                )

        return ToolBoundaryResult(allowed=True)

    def filter_tools(self, tools: list[Any]) -> tuple[list[Any], list[dict[str, Any]]]:
        allowed_tools: list[Any] = []
        blocked: list[dict[str, Any]] = []
        for tool in tools:
            name = _tool_name(tool)
            result = self.tool_boundary_result(name)
            if result.allowed:
                allowed_tools.append(tool)
            else:
                blocked.append(
                    {
                        "tool_name": name,
                        "boundary_key": result.boundary_key,
                        "decision": result.decision,
                        "reason": result.reason,
                    }
                )
        return allowed_tools, blocked

    def before_agent(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return {self.state_key: self.persona_state()}

    def before_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return {self.state_key: self.persona_state()}

    def wrap_model_call(self, request: ModelRequest[Any], handler: Any) -> Any:
        existing_system_message = _system_message_text(request.system_message)
        if not existing_system_message:
            request.system_message = SystemMessage(content=self.system_prompt)
        else:
            request.system_message = SystemMessage(
                content=f"{self.system_prompt}\n\nExisting system message:\n{existing_system_message}"
            )

        if request.tools:
            allowed_tools, blocked = self.filter_tools(list(request.tools))
            request.tools = allowed_tools
            if isinstance(request.state, dict):
                request.state[self.state_key] = {
                    **self.persona_state(),
                    "blocked_tools": blocked,
                }

        return handler(request)

    def wrap_tool_call(self, request: ToolCallRequest, handler: Any) -> ToolMessage | Any:
        tool_name = request.tool_call["name"]
        result = self.tool_boundary_result(tool_name)
        if result.allowed:
            return handler(request)

        reason = result.reason or "The active POP boundary policy blocked this tool."
        return ToolMessage(
            content=(
                f"POP boundary `{result.boundary_key}` blocked tool `{tool_name}`. "
                f"Decision: {result.decision}. {reason}"
            ),
            tool_call_id=request.tool_call["id"],
            name=tool_name,
            status="error",
        )
