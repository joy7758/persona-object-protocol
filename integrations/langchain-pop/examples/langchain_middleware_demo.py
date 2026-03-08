#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def knowledge_lookup(topic: str) -> str:
    """Look up a topic in a mock knowledge base."""
    return f"Knowledge lookup result for: {topic}"


def salary_estimator(role: str) -> str:
    """Estimate salary bands for a role."""
    return f"Salary estimate for: {role}"


def demo_pop_object() -> dict[str, Any]:
    return {
        "kind": "persona-object",
        "id": "persona:mentor:langchain-standalone-demo",
        "version": "1.0.0",
        "role": "mentor",
        "traits": ["calm", "analytical", "structured"],
        "boundaries": {
            "financial_advice": False,
            "tool.salary_estimator": {
                "decision": "disallow",
                "reason": "Salary estimation is outside this mentor persona's approved scope.",
            },
        },
        "status": "active",
        "provenance": {
            "issuer": "langchain-pop-demo",
            "created": "2026-03-08",
        },
    }


def extract_text(result: Any) -> str:
    if isinstance(result, dict):
        messages = result.get("messages")
        if isinstance(messages, list) and messages:
            last = messages[-1]
            content = getattr(last, "content", None)
            if isinstance(content, str):
                return content
            if isinstance(last, dict):
                message_content = last.get("content")
                if isinstance(message_content, str):
                    return message_content
        return json.dumps(result, indent=2, ensure_ascii=True, default=str)
    return str(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Demonstrate POPMiddleware in the standalone langchain-pop package.")
    parser.add_argument(
        "--pop-file",
        help="Optional POP JSON file. If omitted, an inline demo object is used.",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print the generated system prompt and tool filtering report without invoking a model.",
    )
    parser.add_argument(
        "--invoke",
        action="store_true",
        help="Invoke a live LangChain agent. Requires OPENAI_API_KEY and langchain-openai.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("POP_LANGCHAIN_MODEL", "gpt-4.1-mini"),
        help="Model name for langchain_openai.ChatOpenAI",
    )
    parser.add_argument(
        "--message",
        default="How should I plan my career over the next year?",
        help="User message for the live invocation path",
    )
    return parser


def main() -> int:
    try:
        from langchain_pop.agent import create_pop_agent
        from langchain_pop.middleware import POPMiddleware
    except ImportError as exc:
        raise SystemExit(
            "Install the package first: "
            "`pip install -e .`"
        ) from exc

    args = build_parser().parse_args()
    pop_source: str | dict[str, Any] = args.pop_file or demo_pop_object()
    tools = [knowledge_lookup, salary_estimator]
    middleware = POPMiddleware(pop_source)
    allowed_tools, blocked_tools = middleware.filter_tools(tools)

    if args.print_config or not args.invoke:
        print(
            json.dumps(
                {
                    "persona_state": middleware.persona_state(),
                    "system_prompt": middleware.system_prompt,
                    "allowed_tools": [getattr(tool, "name", tool.__name__) for tool in allowed_tools],
                    "blocked_tools": blocked_tools,
                },
                indent=2,
                ensure_ascii=True,
            )
        )
        return 0

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise SystemExit(
            "Install the OpenAI provider extra first: "
            "`pip install -e \\\".[openai]\\\"`"
        ) from exc

    model = ChatOpenAI(model=args.model, api_key=os.environ.get("OPENAI_API_KEY"), temperature=0.0)
    agent = create_pop_agent(
        pop_source=pop_source,
        model=model,
        tools=tools,
        name="standalone_pop_langchain_demo",
    )
    result = agent.invoke({"messages": [{"role": "user", "content": args.message}]})
    print(extract_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
