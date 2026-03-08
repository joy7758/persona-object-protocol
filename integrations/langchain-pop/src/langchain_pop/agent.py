from __future__ import annotations

from typing import Any

from langchain.agents import create_agent

from langchain_pop.middleware import POPMiddleware


def create_pop_agent(
    *,
    pop_source: str | dict[str, Any],
    model: Any,
    tools: list[Any] | None = None,
    middleware: list[Any] | None = None,
    extra_instructions: str | None = None,
    name: str | None = None,
    **kwargs: Any,
) -> Any:
    pop_middleware = POPMiddleware(
        pop_source,
        extra_instructions=extra_instructions,
    )
    middleware_stack = [pop_middleware, *(middleware or [])]
    return create_agent(
        model=model,
        tools=tools or [],
        middleware=middleware_stack,
        name=name,
        **kwargs,
    )
