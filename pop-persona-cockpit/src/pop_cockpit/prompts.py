from __future__ import annotations

from pop_cockpit.schemas import DailyPersonaSnapshot, ImportedRecord

DAILY_EXTRACTION_SYSTEM_PROMPT = """You are generating a concise daily persona snapshot.
Return practical signals, not a chat summary.
Prioritize repeated goals, focus, choices, emotional cues, and explicit decisions.
If signals are weak, say so in confidence notes."""

PERSONA_REBUILD_SYSTEM_PROMPT = """You are consolidating daily persona snapshots into one practical persona core.
Separate stable traits from recent shifts.
Prefer repeated signals over one-off mentions.
Keep the output concise, human-usable, and grounded in the provided snapshots."""

ASK_ANALYSIS_SYSTEM_PROMPT = """You are POP, a persona-guided analysis assistant.
Answer the user's current question using the provided persona core, recent shifts, and retrieved memories.
Stay grounded in the supplied context, note uncertainty when evidence is weak, and keep the answer practical."""


def build_daily_extraction_prompt(
    records: list[ImportedRecord], date_from: str, date_to: str
) -> str:
    record_blocks: list[str] = []
    for record in records:
        preview = record.content.strip()
        if len(preview) > 400:
            preview = f"{preview[:400]}..."
        record_blocks.append(
            "\n".join(
                [
                    f"Record ID: {record.id}",
                    f"Source Type: {record.source_type}",
                    f"Imported At: {record.imported_at.isoformat()}",
                    "Content:",
                    preview,
                ]
            )
        )

    joined_records = "\n\n---\n\n".join(record_blocks)
    return "\n\n".join(
        [
            DAILY_EXTRACTION_SYSTEM_PROMPT,
            f"Date range: {date_from} to {date_to}",
            f"Record count: {len(records)}",
            joined_records,
        ]
    )


def build_persona_rebuild_prompt(
    snapshots: list[DailyPersonaSnapshot], snapshot_scope: str
) -> str:
    snapshot_blocks: list[str] = []
    for snapshot in snapshots:
        snapshot_blocks.append(
            "\n".join(
                [
                    f"Snapshot ID: {snapshot.id}",
                    f"Date range: {snapshot.date_range.date_from} to {snapshot.date_range.date_to}",
                    f"Goal priority: {', '.join(snapshot.goal_priority) or 'none'}",
                    f"Current focus: {', '.join(snapshot.current_focus) or 'none'}",
                    f"Decision style: {snapshot.decision_style or 'none'}",
                    f"Risk profile: {snapshot.risk_profile or 'none'}",
                    f"Recurring topics: {', '.join(snapshot.recurring_topics) or 'none'}",
                    f"Stable biases: {', '.join(snapshot.stable_biases) or 'none'}",
                    f"New traits: {', '.join(snapshot.new_traits) or 'none'}",
                    f"Important decisions: {', '.join(snapshot.important_decisions) or 'none'}",
                    f"Confidence notes: {' | '.join(snapshot.confidence_notes) or 'none'}",
                ]
            )
        )

    return "\n\n".join(
        [
            PERSONA_REBUILD_SYSTEM_PROMPT,
            f"Snapshot scope: {snapshot_scope}",
            f"Snapshot count: {len(snapshots)}",
            "\n\n---\n\n".join(snapshot_blocks),
        ]
    )


def build_ask_analysis_prompt(prompt_package: str) -> str:
    return "\n\n".join(
        [
            "Use the following prepared context package to answer the user's question.",
            prompt_package,
        ]
    )
