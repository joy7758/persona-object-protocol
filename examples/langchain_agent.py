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

from pop_protocol.adapters.langchain import create_langchain_agent, pop_to_langchain_config


def extract_text(result: Any) -> str:
    if isinstance(result, str):
        return result
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
    parser = argparse.ArgumentParser(description="Run a POP persona through a LangChain agent.")
    parser.add_argument("pop_file", help="Path to a POP v1 object or legacy POP 0.1 object")
    parser.add_argument(
        "--model",
        default=os.environ.get("POP_LANGCHAIN_MODEL", "gpt-4.1-mini"),
        help="Model name passed to langchain_openai.ChatOpenAI",
    )
    parser.add_argument(
        "--message",
        default="Introduce yourself and explain how you operate under this persona object.",
        help="User message to send to the LangChain agent",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Chat model temperature",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print the generated LangChain adapter config instead of invoking the model",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = pop_to_langchain_config(args.pop_file)

    if args.print_config:
        print(
            json.dumps(
                {
                    "agent_name": config.agent_name,
                    "persona": config.persona,
                    "constraints": config.constraints,
                    "metadata": config.metadata,
                    "system_prompt": config.system_prompt,
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
            "Install LangChain integration dependencies first: "
            "`pip install -e \".[langchain]\"`"
        ) from exc

    model = ChatOpenAI(model=args.model, temperature=args.temperature)
    agent = create_langchain_agent(args.pop_file, model=model, tools=[])
    result = agent.invoke(
        {"messages": [{"role": "user", "content": args.message}]}
    )
    print(extract_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
