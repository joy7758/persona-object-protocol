from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Iterable

from pop_cockpit.config import AppConfig
from pop_cockpit.llm_api import ProviderError, build_persona_core_with_api, build_provider_client, resolve_task_model
from pop_cockpit.schemas import DailyPersonaSnapshot, PersonaCore
from pop_cockpit.settings import load_project_settings
from pop_cockpit.storage import (
    get_connection,
    get_current_persona_core,
    insert_persona_core_version,
    list_audit_records,
    list_daily_persona_snapshots,
    list_session_records,
)
from pop_cockpit.utils import new_id, utc_now, write_json


@dataclass(slots=True)
class PersonaResult:
    status: str
    message: str
    persona_core: PersonaCore | None = None
    json_path: Path | None = None
    markdown_path: Path | None = None


@dataclass(slots=True)
class PersonaPackageResult:
    status: str
    message: str
    package_path: Path | None = None


@dataclass(slots=True)
class RankedSignal:
    label: str
    normalized: str
    count: int
    score: float
    last_index: int
    is_strong: bool


def rebuild_persona_core(config: AppConfig, snapshot_scope: str = "all") -> PersonaResult:
    with get_connection(config.database_path) as connection:
        snapshots = list_daily_persona_snapshots(connection, snapshot_scope=snapshot_scope)
        if not snapshots:
            return PersonaResult(
                status="empty",
                message=f"No daily snapshots found for scope {snapshot_scope}.",
            )

        settings = load_project_settings(config)
        persona_model = resolve_task_model(settings, "persona")
        if settings.provider_mode in {"api", "hybrid"} and persona_model:
            try:
                persona_core = build_persona_core_with_api(
                    client=build_provider_client(settings),
                    model=persona_model,
                    snapshots=snapshots,
                    snapshot_scope=snapshot_scope,
                )
            except ProviderError as exc:
                if settings.fallback_to_local_on_error:
                    persona_core = aggregate_persona_core(snapshots, snapshot_scope=snapshot_scope)
                    persona_core.confidence_notes.append(
                        f"API unavailable, fell back to local aggregation: {exc}"
                    )
                else:
                    return PersonaResult(
                        status="error",
                        message=f"Persona rebuild failed through AI API: {exc}",
                    )
        else:
            persona_core = aggregate_persona_core(snapshots, snapshot_scope=snapshot_scope)
        json_path, markdown_path = write_persona_core_files(config, persona_core)
        insert_persona_core_version(
            connection,
            version_id=new_id("pcv"),
            persona_core=persona_core,
            markdown_path=markdown_path,
        )
    return PersonaResult(
        status="created",
        message=f"Persona core rebuilt for scope {snapshot_scope}.",
        persona_core=persona_core,
        json_path=json_path,
        markdown_path=markdown_path,
    )


def export_persona_core(config: AppConfig, snapshot_scope: str = "all") -> PersonaResult:
    with get_connection(config.database_path) as connection:
        persona_core = get_current_persona_core(connection, snapshot_scope=snapshot_scope)
    if persona_core is None:
        return PersonaResult(
            status="empty",
            message=f"No persona core found for scope {snapshot_scope}. Run `pop persona rebuild` first.",
        )

    json_path, markdown_path = write_persona_core_files(config, persona_core)
    return PersonaResult(
        status="exported",
        message=f"Persona core exported for scope {snapshot_scope}.",
        persona_core=persona_core,
        json_path=json_path,
        markdown_path=markdown_path,
    )


def show_persona_core(config: AppConfig, snapshot_scope: str = "all") -> PersonaResult:
    with get_connection(config.database_path) as connection:
        persona_core = get_current_persona_core(connection, snapshot_scope=snapshot_scope)
    if persona_core is None:
        return PersonaResult(
            status="empty",
            message=f"No persona core found for scope {snapshot_scope}. Run `pop persona rebuild` first.",
        )
    return PersonaResult(
        status="loaded",
        message=f"Loaded persona core for scope {snapshot_scope}.",
        persona_core=persona_core,
    )


def export_persona_package(
    config: AppConfig,
    *,
    snapshot_scope: str = "all",
    recent_snapshot_limit: int = 14,
    session_limit: int = 10,
) -> PersonaPackageResult:
    with get_connection(config.database_path) as connection:
        persona_core = get_current_persona_core(connection, snapshot_scope=snapshot_scope)
        if persona_core is None:
            return PersonaPackageResult(
                status="empty",
                message=f"No persona core found for scope {snapshot_scope}. Run `pop persona rebuild` first.",
            )
        snapshots = list_daily_persona_snapshots(connection, snapshot_scope=snapshot_scope)[
            -recent_snapshot_limit:
        ]
        sessions = list_session_records(
            connection,
            limit=session_limit,
            snapshot_scope=snapshot_scope,
        )
        audits = list_audit_records(
            connection,
            snapshot_scope=snapshot_scope,
            limit=session_limit,
        )

    scope_label = persona_core_base_name(snapshot_scope).replace("persona_core", "persona_package")
    package_path = config.persona_core_dir / f"{scope_label}.zip"
    manifest = {
        "kind": "pop_persona_package",
        "created_at": utc_now().isoformat(),
        "snapshot_scope": snapshot_scope,
        "persona_core_file": "persona_core.json",
        "daily_snapshots_file": "recent_daily_snapshots.json",
        "sessions_file": "recent_sessions.json",
        "audits_file": "recent_audits.json",
        "counts": {
            "daily_snapshots": len(snapshots),
            "sessions": len(sessions),
            "audits": len(audits),
        },
    }
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr(
            "persona_core.json",
            json.dumps(persona_core.model_dump(mode="json"), ensure_ascii=False, indent=2),
        )
        archive.writestr(
            "recent_daily_snapshots.json",
            json.dumps(
                [snapshot.model_dump(mode="json") for snapshot in snapshots],
                ensure_ascii=False,
                indent=2,
            ),
        )
        archive.writestr(
            "recent_sessions.json",
            json.dumps(
                [session.model_dump(mode="json") for session in sessions],
                ensure_ascii=False,
                indent=2,
            ),
        )
        archive.writestr(
            "recent_audits.json",
            json.dumps(
                [audit.model_dump(mode="json") for audit in audits],
                ensure_ascii=False,
                indent=2,
            ),
        )

    return PersonaPackageResult(
        status="exported",
        message=f"Persona package exported for scope {snapshot_scope}.",
        package_path=package_path,
    )


def format_persona_result(result: PersonaResult) -> str:
    lines = [result.message]
    if result.persona_core is None:
        return "\n".join(lines)
    lines.extend(
        [
            f"snapshot_scope: {result.persona_core.snapshot_scope}",
            f"source_snapshots: {len(result.persona_core.source_snapshot_ids)}",
        ]
    )
    if result.json_path is not None:
        lines.append(f"json: {result.json_path}")
    if result.markdown_path is not None:
        lines.append(f"markdown: {result.markdown_path}")
    return "\n".join(lines)


def format_persona_core_summary(persona_core: PersonaCore) -> str:
    sections = [
        "Persona Core",
        f"scope: {persona_core.snapshot_scope}",
        f"last_updated: {persona_core.last_updated.isoformat() if persona_core.last_updated else 'unknown'}",
        f"identity: {persona_core.identity or 'No stable identity signal detected.'}",
        f"long_term_goals: {', '.join(persona_core.long_term_goals) if persona_core.long_term_goals else 'None detected'}",
        f"current_focus: {', '.join(persona_core.current_focus) if persona_core.current_focus else 'None detected'}",
        f"decision_style: {persona_core.decision_style or 'No clear pattern detected.'}",
        f"risk_profile: {persona_core.risk_profile or 'No clear pattern detected.'}",
        f"stable_biases: {', '.join(persona_core.stable_biases) if persona_core.stable_biases else 'None detected'}",
        f"recurring_topics: {', '.join(persona_core.recurring_topics) if persona_core.recurring_topics else 'None detected'}",
        f"expression_style: {', '.join(persona_core.expression_style) if persona_core.expression_style else 'None detected'}",
        f"taboos_and_boundaries: {', '.join(persona_core.taboos_and_boundaries) if persona_core.taboos_and_boundaries else 'None detected'}",
        f"recent_shifts: {', '.join(persona_core.recent_shifts) if persona_core.recent_shifts else 'None detected'}",
        f"evidence_summary: {' | '.join(persona_core.evidence_summary) if persona_core.evidence_summary else 'None'}",
        f"confidence_notes: {' | '.join(persona_core.confidence_notes) if persona_core.confidence_notes else 'None'}",
        f"source_snapshot_ids: {', '.join(persona_core.source_snapshot_ids)}",
    ]
    return "\n".join(sections)


def write_persona_core_files(config: AppConfig, persona_core: PersonaCore) -> tuple[Path, Path]:
    base_name = persona_core_base_name(persona_core.snapshot_scope)
    json_path = config.persona_core_dir / f"{base_name}.json"
    markdown_path = config.persona_core_dir / f"{base_name}.md"
    write_json(json_path, persona_core.model_dump(mode="json"))
    markdown_path.write_text(render_persona_core_markdown(persona_core), encoding="utf-8")
    return json_path, markdown_path


def render_persona_core_markdown(persona_core: PersonaCore) -> str:
    sections = [
        "# Persona Core",
        "",
        f"- Snapshot scope: {persona_core.snapshot_scope}",
        f"- Last updated: {persona_core.last_updated.isoformat() if persona_core.last_updated else 'unknown'}",
        f"- Source snapshot IDs: {', '.join(persona_core.source_snapshot_ids)}",
        "",
        "## Identity",
        persona_core.identity or "No stable identity signal detected.",
        "",
        "## Long-Term Goals",
        _render_list(persona_core.long_term_goals),
        "",
        "## Current Focus",
        _render_list(persona_core.current_focus),
        "",
        "## Decision Style",
        persona_core.decision_style or "No clear pattern detected.",
        "",
        "## Risk Profile",
        persona_core.risk_profile or "No clear pattern detected.",
        "",
        "## Stable Biases",
        _render_list(persona_core.stable_biases),
        "",
        "## Recurring Topics",
        _render_list(persona_core.recurring_topics),
        "",
        "## Expression Style",
        _render_list(persona_core.expression_style),
        "",
        "## Taboos and Boundaries",
        _render_list(persona_core.taboos_and_boundaries),
        "",
        "## Recent Shifts",
        _render_list(persona_core.recent_shifts),
        "",
        "## Evidence Summary",
        _render_list(persona_core.evidence_summary),
        "",
        "## Confidence Notes",
        _render_list(persona_core.confidence_notes),
    ]
    return "\n".join(sections).strip() + "\n"


def aggregate_persona_core(
    snapshots: list[DailyPersonaSnapshot], snapshot_scope: str = "all"
) -> PersonaCore:
    ordered_snapshots = _dedupe_snapshots_by_date_range(snapshots)
    snapshot_count = len(ordered_snapshots)
    recent_window = max(1, min(3, ceil(snapshot_count / 3)))

    ranked_goals = _rank_list_signals(ordered_snapshots, "goal_priority", recent_window)
    ranked_focus = _rank_list_signals(ordered_snapshots, "current_focus", recent_window)
    ranked_biases = _rank_list_signals(ordered_snapshots, "stable_biases", recent_window)
    ranked_topics = _rank_list_signals(ordered_snapshots, "recurring_topics", recent_window)
    ranked_traits = _rank_list_signals(ordered_snapshots, "new_traits", recent_window)
    ranked_decisions = _rank_list_signals(ordered_snapshots, "important_decisions", recent_window)
    ranked_emotions = _rank_list_signals(ordered_snapshots, "emotional_signals", recent_window)
    ranked_decision_styles = _rank_string_signals(
        ordered_snapshots, "decision_style", recent_window
    )
    ranked_risk_profiles = _rank_string_signals(
        ordered_snapshots, "risk_profile", recent_window
    )

    stable_biases = _select_stable_items(ranked_biases, snapshot_count, limit=4)
    if not stable_biases:
        stable_biases = _select_stable_items(ranked_traits, snapshot_count, limit=3)

    long_term_goals = _select_stable_items(ranked_goals, snapshot_count, limit=4)
    if not long_term_goals:
        long_term_goals = _select_ranked_labels(ranked_goals, limit=3)

    current_focus = _select_current_focus(ranked_focus, snapshot_count)
    recurring_topics = _select_stable_items(ranked_topics, snapshot_count, limit=5)
    recurring_topics = _pad_ranked_labels(recurring_topics, ranked_topics, limit=5)

    decision_style = _select_primary_string(
        ranked_decision_styles,
        snapshot_count,
        fallback="structured but evidence remains limited",
    )
    risk_profile = _select_primary_string(
        ranked_risk_profiles,
        snapshot_count,
        fallback="balanced with limited explicit risk signals",
    )

    recent_shifts = _build_recent_shifts(
        ranked_goals=ranked_goals,
        ranked_focus=ranked_focus,
        ranked_traits=ranked_traits,
        stable_goals=long_term_goals,
        stable_biases=stable_biases,
        recent_window=recent_window,
        limit=5,
    )
    expression_style = _derive_expression_style(
        stable_biases=stable_biases,
        decision_style=decision_style,
        recurring_topics=recurring_topics,
        ranked_emotions=ranked_emotions,
    )
    taboos_and_boundaries = _derive_taboos_and_boundaries(
        stable_biases=stable_biases,
        risk_profile=risk_profile,
        ranked_goals=ranked_goals,
        ranked_decisions=ranked_decisions,
    )
    evidence_summary = _build_evidence_summary(
        ordered_snapshots,
        snapshot_scope=snapshot_scope,
        ranked_biases=ranked_biases,
        ranked_topics=ranked_topics,
    )
    confidence_notes = _build_confidence_notes(
        snapshot_count=snapshot_count,
        ranked_goals=ranked_goals,
        ranked_biases=ranked_biases,
        ranked_decision_styles=ranked_decision_styles,
        ranked_risk_profiles=ranked_risk_profiles,
        stable_goals=long_term_goals,
        stable_biases=stable_biases,
        recent_shifts=recent_shifts,
    )
    identity = _build_identity(
        stable_biases=stable_biases,
        decision_style=decision_style,
        recurring_topics=recurring_topics,
    )

    return PersonaCore(
        identity=identity,
        long_term_goals=long_term_goals,
        current_focus=current_focus,
        decision_style=decision_style,
        risk_profile=risk_profile,
        stable_biases=stable_biases,
        recurring_topics=recurring_topics,
        expression_style=expression_style,
        taboos_and_boundaries=taboos_and_boundaries,
        recent_shifts=recent_shifts,
        evidence_summary=evidence_summary,
        confidence_notes=confidence_notes,
        source_snapshot_ids=[snapshot.id for snapshot in ordered_snapshots],
        snapshot_scope=snapshot_scope,
        last_updated=max(snapshot.created_at for snapshot in ordered_snapshots),
    )


def persona_core_base_name(snapshot_scope: str) -> str:
    if snapshot_scope == "all":
        return "persona_core"
    scope_label = snapshot_scope.replace("source_type:", "").replace("/", "_").replace(" ", "_")
    return f"persona_core__{scope_label}"


def _rank_list_signals(
    snapshots: list[DailyPersonaSnapshot],
    field_name: str,
    recent_window: int,
) -> list[RankedSignal]:
    signal_data: dict[str, dict[str, float | int | bool | str]] = {}
    snapshot_count = len(snapshots)
    for index, snapshot in enumerate(snapshots):
        items = list(dict.fromkeys(getattr(snapshot, field_name)))
        recency_bonus = 0.35 if index >= snapshot_count - recent_window else 0.0
        for item in items:
            if _looks_like_json_property(item):
                continue
            normalized = _normalize_text(item)
            if not normalized:
                continue
            if normalized not in signal_data:
                signal_data[normalized] = {
                    "label": item,
                    "count": 0,
                    "score": 0.0,
                    "last_index": index,
                    "is_strong": _is_strong_signal(item),
                }
            signal_data[normalized]["count"] += 1
            signal_data[normalized]["score"] += 1.0 + recency_bonus
            signal_data[normalized]["last_index"] = index
            signal_data[normalized]["is_strong"] = bool(signal_data[normalized]["is_strong"]) or _is_strong_signal(item)

    ranked = [
        RankedSignal(
            label=str(payload["label"]),
            normalized=normalized,
            count=int(payload["count"]),
            score=float(payload["score"]),
            last_index=int(payload["last_index"]),
            is_strong=bool(payload["is_strong"]),
        )
        for normalized, payload in signal_data.items()
    ]
    return sorted(ranked, key=lambda signal: (-signal.score, -signal.count, signal.label.lower()))


def _rank_string_signals(
    snapshots: list[DailyPersonaSnapshot],
    field_name: str,
    recent_window: int,
) -> list[RankedSignal]:
    normalized_snapshots: list[DailyPersonaSnapshot] = []
    for snapshot in snapshots:
        value = getattr(snapshot, field_name)
        if isinstance(value, str) and value.strip():
            normalized_snapshots.append(snapshot)
    return _rank_list_signals_for_strings(normalized_snapshots, field_name, recent_window)


def _rank_list_signals_for_strings(
    snapshots: list[DailyPersonaSnapshot], field_name: str, recent_window: int
) -> list[RankedSignal]:
    signal_data: dict[str, dict[str, float | int | bool | str]] = {}
    snapshot_count = len(snapshots)
    for index, snapshot in enumerate(snapshots):
        item = getattr(snapshot, field_name).strip()
        if _looks_like_json_property(item):
            continue
        normalized = _normalize_text(item)
        if not normalized:
            continue
        recency_bonus = 0.35 if index >= snapshot_count - recent_window else 0.0
        if normalized not in signal_data:
            signal_data[normalized] = {
                "label": item,
                "count": 0,
                "score": 0.0,
                "last_index": index,
                "is_strong": _is_strong_signal(item),
            }
        signal_data[normalized]["count"] += 1
        signal_data[normalized]["score"] += 1.0 + recency_bonus
        signal_data[normalized]["last_index"] = index
        signal_data[normalized]["is_strong"] = bool(signal_data[normalized]["is_strong"]) or _is_strong_signal(item)
    ranked = [
        RankedSignal(
            label=str(payload["label"]),
            normalized=normalized,
            count=int(payload["count"]),
            score=float(payload["score"]),
            last_index=int(payload["last_index"]),
            is_strong=bool(payload["is_strong"]),
        )
        for normalized, payload in signal_data.items()
    ]
    return sorted(ranked, key=lambda signal: (-signal.score, -signal.count, signal.label.lower()))


def _select_stable_items(
    ranked_signals: list[RankedSignal], snapshot_count: int, limit: int
) -> list[str]:
    stable: list[str] = []
    for signal in ranked_signals:
        if snapshot_count == 1:
            stable.append(signal.label)
        elif signal.count >= 2:
            stable.append(signal.label)
        elif snapshot_count <= 2 and signal.is_strong:
            stable.append(signal.label)
        if len(stable) >= limit:
            break
    return stable


def _select_ranked_labels(ranked_signals: list[RankedSignal], limit: int) -> list[str]:
    return [signal.label for signal in ranked_signals[:limit]]


def _pad_ranked_labels(selected: list[str], ranked_signals: list[RankedSignal], limit: int) -> list[str]:
    ordered = list(selected)
    existing = {_normalize_text(value) for value in ordered}
    for signal in ranked_signals:
        if signal.normalized in existing:
            continue
        ordered.append(signal.label)
        existing.add(signal.normalized)
        if len(ordered) >= limit:
            break
    return ordered[:limit]


def _select_current_focus(ranked_focus: list[RankedSignal], snapshot_count: int) -> list[str]:
    if snapshot_count <= 2:
        return _select_ranked_labels(ranked_focus, limit=3)
    focus = [
        signal.label
        for signal in ranked_focus
        if signal.last_index >= snapshot_count - max(1, min(3, ceil(snapshot_count / 3)))
    ]
    if focus:
        return focus[:3]
    return _select_ranked_labels(ranked_focus, limit=3)


def _select_primary_string(
    ranked_signals: list[RankedSignal], snapshot_count: int, fallback: str
) -> str:
    if not ranked_signals:
        return fallback
    top_signal = ranked_signals[0]
    if snapshot_count <= 2 or top_signal.count >= 2 or top_signal.is_strong:
        return top_signal.label
    return f"{top_signal.label} (weak confidence)"


def _build_recent_shifts(
    *,
    ranked_goals: list[RankedSignal],
    ranked_focus: list[RankedSignal],
    ranked_traits: list[RankedSignal],
    stable_goals: list[str],
    stable_biases: list[str],
    recent_window: int,
    limit: int,
) -> list[str]:
    stable_set = {_normalize_text(value) for value in [*stable_goals, *stable_biases]}
    candidates: list[str] = []
    for prefix, ranked_signals in (
        ("goal", ranked_goals),
        ("focus", ranked_focus),
        ("trait", ranked_traits),
    ):
        for signal in ranked_signals:
            if signal.normalized in stable_set:
                continue
            if signal.count == 1 and signal.last_index >= 0:
                candidates.append(f"{prefix}: {signal.label}")
    deduped = list(dict.fromkeys(candidates))
    return deduped[:limit]


def _derive_expression_style(
    *,
    stable_biases: list[str],
    decision_style: str,
    recurring_topics: list[str],
    ranked_emotions: list[RankedSignal],
) -> list[str]:
    style: list[str] = []
    joined_biases = " ".join(stable_biases).lower()
    if any(keyword in joined_biases for keyword in ("readable", "clarity", "simple")):
        style.append("direct and readability-focused")
    if any(keyword in decision_style.lower() for keyword in ("structured", "analytical", "comparison")):
        style.append("structured and analytical")
    if any(keyword in " ".join(recurring_topics).lower() for keyword in ("system", "persona", "cockpit", "tooling")):
        style.append("system-oriented")
    if ranked_emotions and ranked_emotions[0].label in {"confidence", "calm"}:
        style.append("steady and low-drama")
    if not style:
        style.append("plain-spoken and task-oriented")
    return style[:4]


def _derive_taboos_and_boundaries(
    *,
    stable_biases: list[str],
    risk_profile: str,
    ranked_goals: list[RankedSignal],
    ranked_decisions: list[RankedSignal],
) -> list[str]:
    boundaries: list[str] = []
    for signal in [*ranked_goals, *ranked_decisions]:
        lowered = signal.label.lower()
        if any(keyword in lowered for keyword in ("avoid", "no ", "not ", "without", "never")):
            boundaries.append(signal.label)
    joined_biases = " ".join(stable_biases).lower()
    if "local-first" in joined_biases:
        boundaries.append("Avoid unnecessary cloud dependency unless it is clearly justified.")
    if any(keyword in joined_biases for keyword in ("simple", "readable")):
        boundaries.append("Avoid unnecessary abstraction and opaque complexity.")
    if "cautious" in risk_profile.lower() or "validation" in risk_profile.lower():
        boundaries.append("Avoid unvalidated changes to core behavior.")
    return list(dict.fromkeys(boundaries))[:4]


def _build_evidence_summary(
    snapshots: list[DailyPersonaSnapshot],
    *,
    snapshot_scope: str,
    ranked_biases: list[RankedSignal],
    ranked_topics: list[RankedSignal],
) -> list[str]:
    summary = [
        (
            f"Built from {len(snapshots)} daily snapshots spanning "
            f"{snapshots[0].date_range.date_from} to {snapshots[-1].date_range.date_to} "
            f"in scope {snapshot_scope}."
        ),
        "Stable traits were promoted when they repeated across multiple snapshots or had strong phrasing.",
    ]
    repeated_biases = [signal for signal in ranked_biases if signal.count >= 2][:2]
    if repeated_biases:
        summary.append(
            "Repeated biases: "
            + ", ".join(f"{signal.label} ({signal.count})" for signal in repeated_biases)
        )
    repeated_topics = [signal for signal in ranked_topics if signal.count >= 2][:3]
    if repeated_topics:
        summary.append(
            "Repeated topics: "
            + ", ".join(f"{signal.label} ({signal.count})" for signal in repeated_topics)
        )
    return summary


def _build_confidence_notes(
    *,
    snapshot_count: int,
    ranked_goals: list[RankedSignal],
    ranked_biases: list[RankedSignal],
    ranked_decision_styles: list[RankedSignal],
    ranked_risk_profiles: list[RankedSignal],
    stable_goals: list[str],
    stable_biases: list[str],
    recent_shifts: list[str],
) -> list[str]:
    notes: list[str] = []
    stable_goal_set = {_normalize_text(value) for value in stable_goals}
    stable_bias_set = {_normalize_text(value) for value in stable_biases}
    if snapshot_count < 3:
        notes.append(
            f"Confidence is limited because the core is built from only {snapshot_count} daily snapshot(s)."
        )
    if ranked_decision_styles and ranked_decision_styles[0].count == 1 and snapshot_count > 1:
        notes.append("Decision style is still based on limited evidence.")
    if ranked_risk_profiles and ranked_risk_profiles[0].count == 1 and snapshot_count > 1:
        notes.append("Risk profile is still based on limited evidence.")
    weak_biases = [
        signal.label
        for signal in ranked_biases
        if signal.count == 1 and signal.normalized not in stable_bias_set
    ][:3]
    if weak_biases:
        notes.append("Weak bias signals were not promoted to stable traits: " + ", ".join(weak_biases))
    weak_goals = [
        signal.label
        for signal in ranked_goals
        if signal.count == 1 and signal.normalized not in stable_goal_set
    ][:3]
    if weak_goals:
        notes.append("One-off goals were kept out of the long-term core: " + ", ".join(weak_goals))
    if recent_shifts:
        notes.append("Recent shifts remain separate until they repeat across additional snapshots.")
    return notes[:5]


def _build_identity(
    *,
    stable_biases: list[str],
    decision_style: str,
    recurring_topics: list[str],
) -> str:
    descriptors: list[str] = []
    joined_biases = " ".join(stable_biases).lower()
    if "local-first" in joined_biases:
        descriptors.append("local-first")
    if any(keyword in joined_biases for keyword in ("readable", "simple")):
        descriptors.append("readability-focused")
    if any(keyword in joined_biases for keyword in ("verification", "determinism")):
        descriptors.append("verification-oriented")

    subject = "builder"
    if any(topic in {"persona", "cockpit", "system", "systems"} for topic in recurring_topics):
        subject = "system builder"

    if descriptors:
        if len(descriptors) == 1:
            prefix = descriptors[0]
        else:
            prefix = ", ".join(descriptors[:-1]) + f", and {descriptors[-1]}"
        identity = f"A {prefix} {subject}"
    else:
        identity = f"A practical {subject}"

    if decision_style:
        identity += f" who tends to be {decision_style}"
    return identity + "."


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split()).strip()


def _is_strong_signal(value: str) -> bool:
    lowered = value.lower()
    strong_keywords = (
        "must",
        "avoid",
        "always",
        "never",
        "priority",
        "decision",
        "prefer",
        "bias",
        "validation",
    )
    return any(keyword in lowered for keyword in strong_keywords)


def _looks_like_json_property(value: str) -> bool:
    stripped = value.strip()
    return stripped.startswith('"') and '":' in stripped


def _dedupe_snapshots_by_date_range(
    snapshots: list[DailyPersonaSnapshot],
) -> list[DailyPersonaSnapshot]:
    latest_by_range: dict[tuple[str, str], DailyPersonaSnapshot] = {}
    for snapshot in sorted(
        snapshots,
        key=lambda candidate: (
            candidate.date_range.date_from,
            candidate.date_range.date_to,
            candidate.created_at,
            candidate.id,
        ),
    ):
        latest_by_range[(snapshot.date_range.date_from, snapshot.date_range.date_to)] = snapshot
    return list(latest_by_range.values())


def _render_list(items: Iterable[str]) -> str:
    rendered_items = [item for item in items if item]
    if not rendered_items:
        return "- None detected"
    return "\n".join(f"- {item}" for item in rendered_items)
