from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

StageOutputBuilder = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class TaskTypeDefinition:
    task_type: str
    deliverable_type: str
    handlers: dict[str, StageOutputBuilder]


TASK_REGISTRY: dict[str, TaskTypeDefinition] = {}


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


def build_stage_output(
    task_type: str,
    stage_name: str,
    task_input: dict[str, Any],
) -> dict[str, Any]:
    definition = get_task_definition(task_type)
    try:
        builder = definition.handlers[stage_name]
    except KeyError as exc:
        raise ValueError(
            f"Task type `{task_type}` does not define a `{stage_name}` handler."
        ) from exc
    return builder(task_input)


def deliverable_type_for(task_type: str) -> str:
    return get_task_definition(task_type).deliverable_type


def subject_inputs(task_input: dict[str, Any]) -> dict[str, Any]:
    return task_input.get("inputs", {})


def summarize_subject(task_input: dict[str, Any]) -> str:
    inputs = subject_inputs(task_input)
    feature_list = ", ".join(inputs.get("subject_attributes", [])) or "core attributes"
    return (
        f"{inputs.get('subject_name', 'Unknown subject')} in "
        f"{inputs.get('subject_category', 'Unknown')}"
        f" with {feature_list}"
    )


def with_indefinite_article(text: str) -> str:
    article = "an" if text[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {text}"


def infer_market_trends(task_input: dict[str, Any]) -> list[str]:
    inputs = subject_inputs(task_input)
    features = {str(feature).lower() for feature in inputs.get("subject_attributes", [])}
    trends: list[str] = []
    if "5g" in features:
        trends.append("5G adoption remains a purchase driver in premium devices")
    if "fast charging" in features:
        trends.append("Battery convenience influences upgrade decisions")
    if "touchscreen" in features:
        trends.append("Large responsive displays remain central to daily usage")
    if str(inputs.get("subject_category", "")).lower() == "electronics":
        trends.append("Consumers compare feature density with price sensitivity")
    return trends or ["General market demand should be validated with recent signals"]


def infer_design_constraints(task_input: dict[str, Any]) -> list[str]:
    inputs = subject_inputs(task_input)
    constraints = inputs.get("constraints", [])
    if constraints:
        return constraints
    return [
        "Balance concept ambition with implementation feasibility",
        "Keep differentiation obvious to the target audience",
    ]


def infer_ux_findings(task_input: dict[str, Any]) -> list[str]:
    inputs = subject_inputs(task_input)
    attributes = {str(item).lower() for item in inputs.get("subject_attributes", [])}
    findings: list[str] = []
    if "form abandonment" in attributes:
        findings.append("Long form steps likely interrupt momentum before payment.")
    if "payment trust" in attributes:
        findings.append("Trust cues near payment decisions need to be more visible.")
    if "mobile checkout" in attributes:
        findings.append("Mobile users need fewer taps and clearer progress markers.")
    return findings or [
        "Review friction around the primary user path and prioritize the highest drop-off points."
    ]


def objective_for(
    task_input: dict[str, Any],
    index: int,
    default: str,
) -> str:
    objectives = task_input.get("objectives", [])
    if index < len(objectives):
        return str(objectives[index])
    return default


def build_market_research_design_output(task_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": f"Design a concept for {summarize_subject(task_input)}",
        "objective": objective_for(task_input, 0, "Design a product concept"),
        "subject": subject_inputs(task_input),
        "focus": [
            "clarify the value proposition",
            "connect concept choices to buyer expectations",
            "prepare a market-aware design brief",
        ],
    }


def build_market_research_research_output(task_input: dict[str, Any]) -> dict[str, Any]:
    inputs = subject_inputs(task_input)
    return {
        "summary": f"Research market demand for {inputs['subject_name']}",
        "objective": objective_for(task_input, 1, "Research market trends"),
        "market_trends": infer_market_trends(task_input),
        "focus": [
            "collect supporting market signals",
            "distill concise findings",
            "translate evidence into technical context",
        ],
    }


def build_market_research_marketing_output(task_input: dict[str, Any]) -> dict[str, Any]:
    inputs = subject_inputs(task_input)
    attributes = ", ".join(inputs["subject_attributes"])
    hero_attribute = (
        inputs["subject_attributes"][0]
        if inputs["subject_attributes"]
        else "the clearest differentiator"
    )
    return {
        "summary": f"Create marketing strategy for {inputs['subject_name']}",
        "objective": objective_for(task_input, 2, "Create marketing strategy"),
        "positioning": (
            f"{inputs['subject_name']} is positioned as "
            f"{with_indefinite_article(inputs['subject_category'].lower())} offer that "
            f"combines {attributes} into one concise value story."
        ),
        "campaign_hooks": [
            f"Lead with {hero_attribute} as the hero differentiator",
            "Use research-backed proof points in launch messaging",
            "Connect product utility to everyday buyer outcomes",
        ],
        "focus": [
            "turn research into positioning",
            "shape a campaign-ready narrative",
            "package the final deliverable",
        ],
    }


def build_product_design_design_output(task_input: dict[str, Any]) -> dict[str, Any]:
    inputs = subject_inputs(task_input)
    return {
        "summary": (
            f"Shape the product direction for {inputs['subject_name']} with "
            "attention to concept clarity and buildability"
        ),
        "objective": objective_for(task_input, 0, "Shape the product concept"),
        "concept_direction": {
            "subject": inputs["subject_name"],
            "category": inputs["subject_category"],
            "hero_attributes": inputs["subject_attributes"][:3],
        },
        "focus": [
            "define the concept direction",
            "prioritize user-facing differentiators",
            "keep the concept buildable under constraints",
        ],
    }


def build_product_design_research_output(task_input: dict[str, Any]) -> dict[str, Any]:
    inputs = subject_inputs(task_input)
    return {
        "summary": f"Research constraints and adjacent patterns for {inputs['subject_name']}",
        "objective": objective_for(
            task_input,
            1,
            "Review design constraints and competitive cues",
        ),
        "design_constraints": infer_design_constraints(task_input),
        "focus": [
            "compare adjacent product patterns",
            "identify feasibility and usability constraints",
            "surface practical tradeoffs for the concept",
        ],
    }


def build_product_design_marketing_output(task_input: dict[str, Any]) -> dict[str, Any]:
    inputs = subject_inputs(task_input)
    attributes = ", ".join(inputs["subject_attributes"])
    return {
        "summary": f"Prepare launch framing for the {inputs['subject_name']} concept",
        "objective": objective_for(
            task_input,
            2,
            "Prepare launch messaging for the concept",
        ),
        "launch_story": (
            f"Present {inputs['subject_name']} as a concept that turns {attributes} "
            "into a coherent premium product direction."
        ),
        "stakeholder_hooks": [
            "Frame the concept as feasible, differentiated, and buyer-relevant",
            "Use constraints to explain why the chosen direction is disciplined",
        ],
        "focus": [
            "translate the concept into launch language",
            "align story with buyer expectations",
            "package the concept as a reviewable brief",
        ],
    }


def build_ux_review_design_output(task_input: dict[str, Any]) -> dict[str, Any]:
    inputs = subject_inputs(task_input)
    return {
        "summary": (
            f"Define an improved experience for {inputs['subject_name']} in "
            f"{inputs['subject_category']}"
        ),
        "objective": objective_for(task_input, 0, "Define a better checkout experience"),
        "experience_map": {
            "subject": inputs["subject_name"],
            "primary_friction_signals": inputs["subject_attributes"][:3],
            "target_audience": inputs.get("target_audience"),
        },
        "focus": [
            "map the intended user journey",
            "reduce points of hesitation",
            "prepare a concise improvement concept",
        ],
    }


def build_ux_review_research_output(task_input: dict[str, Any]) -> dict[str, Any]:
    inputs = subject_inputs(task_input)
    return {
        "summary": f"Research UX friction patterns for {inputs['subject_name']}",
        "objective": objective_for(task_input, 1, "Identify friction and usage patterns"),
        "ux_findings": infer_ux_findings(task_input),
        "focus": [
            "identify friction signals",
            "connect issues to user behavior patterns",
            "prioritize what should change first",
        ],
    }


def build_ux_review_marketing_output(task_input: dict[str, Any]) -> dict[str, Any]:
    inputs = subject_inputs(task_input)
    return {
        "summary": f"Package the UX rollout plan for {inputs['subject_name']}",
        "objective": objective_for(
            task_input,
            2,
            "Package the UX improvement plan for rollout",
        ),
        "rollout_story": (
            f"Position the {inputs['subject_name']} update as a friction-reduction effort "
            "that improves confidence and completion rates."
        ),
        "stakeholder_hooks": [
            "Tie each improvement to a visible user pain point",
            "Explain the rollout in terms of reduced friction and clearer trust cues",
        ],
        "focus": [
            "frame the UX work for stakeholders",
            "turn findings into an adoption story",
            "package a rollout-ready improvement plan",
        ],
    }


register_task_type(
    TaskTypeDefinition(
        task_type="market_research",
        deliverable_type="market_strategy_report",
        handlers={
            "design": build_market_research_design_output,
            "research": build_market_research_research_output,
            "marketing": build_market_research_marketing_output,
        },
    )
)

register_task_type(
    TaskTypeDefinition(
        task_type="product_design",
        deliverable_type="product_concept_brief",
        handlers={
            "design": build_product_design_design_output,
            "research": build_product_design_research_output,
            "marketing": build_product_design_marketing_output,
        },
    )
)

register_task_type(
    TaskTypeDefinition(
        task_type="ux_review",
        deliverable_type="ux_improvement_plan",
        handlers={
            "design": build_ux_review_design_output,
            "research": build_ux_review_research_output,
            "marketing": build_ux_review_marketing_output,
        },
    )
)
