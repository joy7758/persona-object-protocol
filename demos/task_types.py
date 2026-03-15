from __future__ import annotations

from demos.task_registry import StageDefinition, TaskTypeDefinition


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


BUILTIN_TASK_TYPES = (
    TaskTypeDefinition(
        task_type="market_research",
        deliverable_type="market_strategy_report",
        stage_sequence=COMMON_STAGE_SEQUENCE,
        stage_handlers={
            "design": "market_research.design",
            "research": "market_research.research",
            "marketing": "market_research.marketing",
        },
    ),
    TaskTypeDefinition(
        task_type="product_design",
        deliverable_type="product_concept_brief",
        stage_sequence=COMMON_STAGE_SEQUENCE,
        stage_handlers={
            "design": "product_design.design",
            "research": "product_design.research",
            "marketing": "product_design.marketing",
        },
    ),
    TaskTypeDefinition(
        task_type="ux_review",
        deliverable_type="ux_improvement_plan",
        stage_sequence=COMMON_STAGE_SEQUENCE,
        stage_handlers={
            "design": "ux_review.design",
            "research": "ux_review.research",
            "marketing": "ux_review.marketing",
        },
    ),
)
