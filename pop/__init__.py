"""POP package public API.

This top-level package combines:
- the canonical SDK surface that lives under ``src/pop``
- the local prototype modules added at the repository root

The repository currently contains both trees. Extending ``__path__``
lets ``import pop.*`` resolve the established implementation under
``src/pop`` while keeping the root-level prototype modules available.
"""

from pathlib import Path


_SRC_POP_PATH = Path(__file__).resolve().parents[1] / "src" / "pop"
if _SRC_POP_PATH.exists():
    _src_pop_str = str(_SRC_POP_PATH)
    if _src_pop_str not in __path__:
        __path__.insert(0, _src_pop_str)


from pop.adapters import BasePersonaAdapter, CrewAIAdapter, LangChainAdapter
from pop.integrations.crewai import (
    bind_crewai_agent_kwargs,
    create_crewai_agent_kwargs,
    create_crewai_agent_from_persona,
    create_crewai_execution_scaffold,
)
from pop.integrations.langchain import (
    bind_langchain_context,
    bind_langchain_middleware,
    bind_langchain_prompt,
    create_langchain_context_bundle,
    create_langchain_create_agent_kwargs,
    create_langchain_agent_kwargs,
    create_langchain_execution_bundle,
    create_langchain_execution_scaffold,
    create_langchain_middleware_bundle,
    create_langchain_middleware_scaffold,
    maybe_build_langchain_agent_spec,
)
from pop.io import load_persona, save_persona
from pop.models import PersonaObject
from pop.schema import (
    get_schema_id,
    list_available_schema_versions,
    load_pop_schema,
    load_pop_schema_version,
)
from pop.validate import (
    PersonaValidationError,
    validate_persona,
    validate_persona_schema,
    validate_persona_schema_dict,
)

from .adapter_autogen import assistant_agent_from_persona, agent_from_persona
from .registry import (
    list_persona_ids,
    list_personas,
    load_persona_by_id,
    normalize_persona_ref,
    resolve_persona,
)

__all__ = [
    "PersonaObject",
    "PersonaValidationError",
    "BasePersonaAdapter",
    "CrewAIAdapter",
    "LangChainAdapter",
    "assistant_agent_from_persona",
    "agent_from_persona",
    "bind_crewai_agent_kwargs",
    "bind_langchain_context",
    "bind_langchain_middleware",
    "bind_langchain_prompt",
    "create_crewai_agent_kwargs",
    "create_crewai_agent_from_persona",
    "create_crewai_execution_scaffold",
    "create_langchain_context_bundle",
    "create_langchain_create_agent_kwargs",
    "create_langchain_agent_kwargs",
    "create_langchain_execution_bundle",
    "create_langchain_execution_scaffold",
    "create_langchain_middleware_bundle",
    "create_langchain_middleware_scaffold",
    "get_schema_id",
    "list_available_schema_versions",
    "list_persona_ids",
    "list_personas",
    "load_persona",
    "load_persona_by_id",
    "load_pop_schema",
    "load_pop_schema_version",
    "maybe_build_langchain_agent_spec",
    "normalize_persona_ref",
    "resolve_persona",
    "save_persona",
    "validate_persona",
    "validate_persona_schema",
    "validate_persona_schema_dict",
]
