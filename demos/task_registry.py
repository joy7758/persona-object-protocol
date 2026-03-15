from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

StageOutputBuilder = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class PersonaDefinition:
    persona_id: str
    file_path: str


@dataclass(frozen=True)
class StageHandlerDefinition:
    handler_id: str
    builder: StageOutputBuilder


@dataclass(frozen=True)
class StageDefinition:
    stage_name: str
    persona_id: str
    progress_label: str
    deliverable_section: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskTypeDefinition:
    task_type: str
    deliverable_type: str
    stage_sequence: tuple[StageDefinition, ...]
    stage_handlers: dict[str, str]


PERSONA_REGISTRY: dict[str, PersonaDefinition] = {}
STAGE_HANDLER_REGISTRY: dict[str, StageHandlerDefinition] = {}
TASK_REGISTRY: dict[str, TaskTypeDefinition] = {}


def register_persona(definition: PersonaDefinition) -> None:
    PERSONA_REGISTRY[definition.persona_id] = definition


def get_persona_definition(persona_id: str) -> PersonaDefinition:
    try:
        return PERSONA_REGISTRY[persona_id]
    except KeyError as exc:
        available = ", ".join(sorted(PERSONA_REGISTRY))
        raise ValueError(
            f"Unknown persona `{persona_id}`. Expected one of: {available}."
        ) from exc


def persona_path_for(persona_id: str) -> str:
    return get_persona_definition(persona_id).file_path


def register_stage_handler(definition: StageHandlerDefinition) -> None:
    STAGE_HANDLER_REGISTRY[definition.handler_id] = definition


def get_stage_handler_definition(handler_id: str) -> StageHandlerDefinition:
    try:
        return STAGE_HANDLER_REGISTRY[handler_id]
    except KeyError as exc:
        available = ", ".join(sorted(STAGE_HANDLER_REGISTRY))
        raise ValueError(
            f"Unknown stage handler `{handler_id}`. Expected one of: {available}."
        ) from exc


def registered_stage_handler_ids() -> frozenset[str]:
    return frozenset(STAGE_HANDLER_REGISTRY)


def register_task_type(definition: TaskTypeDefinition) -> None:
    TASK_REGISTRY[definition.task_type] = definition


def supported_task_types() -> frozenset[str]:
    return frozenset(TASK_REGISTRY)


def get_task_definition(task_type: str) -> TaskTypeDefinition:
    try:
        return TASK_REGISTRY[task_type]
    except KeyError as exc:
        supported = ", ".join(sorted(TASK_REGISTRY))
        raise ValueError(
            f"Unsupported `task_type`: {task_type or '(missing)'}. Expected one of: {supported}."
        ) from exc


def stage_handler_id_for(task_type: str, stage_name: str) -> str:
    definition = get_task_definition(task_type)
    try:
        return definition.stage_handlers[stage_name]
    except KeyError as exc:
        raise ValueError(
            f"Task type `{task_type}` does not define a `{stage_name}` handler."
        ) from exc


def build_stage_output(
    task_type: str,
    stage_name: str,
    task_input: dict[str, Any],
) -> dict[str, Any]:
    handler_id = stage_handler_id_for(task_type, stage_name)
    handler = get_stage_handler_definition(handler_id)
    return handler.builder(task_input)


def stage_sequence_for(task_type: str) -> tuple[StageDefinition, ...]:
    return get_task_definition(task_type).stage_sequence


def persona_sequence_for(task_type: str) -> tuple[str, ...]:
    return tuple(stage.persona_id for stage in stage_sequence_for(task_type))


def deliverable_type_for(task_type: str) -> str:
    return get_task_definition(task_type).deliverable_type


def build_deliverable(task_type: str, context: Any) -> dict[str, Any]:
    definition = get_task_definition(task_type)
    persona_sequence: list[str] = []
    stage_sequence: list[str] = []
    stage_outputs: dict[str, dict[str, Any]] = {}

    deliverable = {
        "task_name": context.task_name,
        "task_type": context.task_type,
        "deliverable_type": definition.deliverable_type,
        "inputs": context.task_input.get("inputs", {}),
        "objectives": context.task_input.get("objectives", []),
        "stage_handlers": dict(definition.stage_handlers),
    }

    for stage in definition.stage_sequence:
        result = context.get_stage_result(stage.stage_name)
        if not result:
            continue
        persona_name = str(result.get("persona_name") or stage.persona_id)
        persona_sequence.append(persona_name)
        stage_sequence.append(stage.stage_name)
        task_output = result.get("task_output", {})
        stage_outputs[stage.stage_name] = task_output
        deliverable[stage.deliverable_section] = task_output

    deliverable["prepared_by"] = persona_sequence[-1] if persona_sequence else ""
    deliverable["persona_sequence"] = persona_sequence
    deliverable["stage_sequence"] = stage_sequence
    deliverable["stage_outputs"] = stage_outputs
    return deliverable


COMMON_STAGE_SEQUENCE = (
    StageDefinition(
        stage_name="design",
        persona_id="design_persona",
        progress_label="Designing",
        deliverable_section="design_brief",
    ),
    StageDefinition(
        stage_name="research",
        persona_id="research_persona",
        progress_label="Researching",
        deliverable_section="research_summary",
        depends_on=("design",),
    ),
    StageDefinition(
        stage_name="marketing",
        persona_id="marketing_persona",
        progress_label="Marketing",
        deliverable_section="marketing_plan",
        depends_on=("design", "research"),
    ),
)


register_persona(
    PersonaDefinition(
        persona_id="design_persona",
        file_path="personas/design_persona.json",
    )
)
register_persona(
    PersonaDefinition(
        persona_id="research_persona",
        file_path="personas/researcher_persona.json",
    )
)
register_persona(
    PersonaDefinition(
        persona_id="marketing_persona",
        file_path="personas/marketing_persona.json",
    )
)


from demos import stage_handlers as _stage_handlers


register_task_type(
    TaskTypeDefinition(
        task_type="market_research",
        deliverable_type="market_strategy_report",
        stage_sequence=COMMON_STAGE_SEQUENCE,
        stage_handlers={
            "design": "market_research.design",
            "research": "market_research.research",
            "marketing": "market_research.marketing",
        },
    )
)

register_task_type(
    TaskTypeDefinition(
        task_type="product_design",
        deliverable_type="product_concept_brief",
        stage_sequence=COMMON_STAGE_SEQUENCE,
        stage_handlers={
            "design": "product_design.design",
            "research": "product_design.research",
            "marketing": "product_design.marketing",
        },
    )
)

register_task_type(
    TaskTypeDefinition(
        task_type="ux_review",
        deliverable_type="ux_improvement_plan",
        stage_sequence=COMMON_STAGE_SEQUENCE,
        stage_handlers={
            "design": "ux_review.design",
            "research": "ux_review.research",
            "marketing": "ux_review.marketing",
        },
    )
)
