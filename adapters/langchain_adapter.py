from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pop_protocol.adapters.langchain import (
    LangChainPersonaConfig,
    build_langchain_system_prompt,
    create_langchain_agent,
    pop_to_langchain_config,
)

__all__ = [
    "LangChainPersonaConfig",
    "build_langchain_system_prompt",
    "create_langchain_agent",
    "pop_to_langchain_config",
]
