from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from pop_cockpit.audit import ensure_audit_record
from pop_cockpit.config import AppConfig
from pop_cockpit.extractor import resolve_effective_event_timestamp
from pop_cockpit.llm_api import (
    OpenAICompatibleAskProvider,
    ProviderError,
    build_provider_client,
    resolve_task_model,
)
from pop_cockpit.schemas import DailyPersonaSnapshot, ImportedRecord, PersonaCore, SessionRecord
from pop_cockpit.settings import load_project_settings
from pop_cockpit.storage import (
    get_connection,
    get_current_persona_core_version,
    insert_session_record,
    list_daily_persona_snapshots,
    list_imported_records,
)
from pop_cockpit.utils import new_id, utc_now, write_json

QUESTION_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "do",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "should",
    "that",
    "the",
    "this",
    "to",
    "today",
    "what",
    "with",
}

PERSONA_FIELDS = [
    "identity",
    "long_term_goals",
    "current_focus",
    "decision_style",
    "risk_profile",
    "stable_biases",
    "recurring_topics",
    "expression_style",
    "taboos_and_boundaries",
    "recent_shifts",
    "evidence_summary",
    "confidence_notes",
]


class AskProvider:
    name = "provider"

    def answer(self, prompt_context: str) -> str:
        raise NotImplementedError


@dataclass(slots=True)
class AskResult:
    status: str
    message: str
    session: SessionRecord | None = None
    prompt_package: str = ""
    persona_core: PersonaCore | None = None
    recent_snapshots: list[DailyPersonaSnapshot] = field(default_factory=list)
    retrieval_notes: list[dict[str, Any]] = field(default_factory=list)
    used_memory_ids: list[str] = field(default_factory=list)
    persisted: bool = True
    json_path: Path | None = None
    markdown_path: Path | None = None
    engine_mode: str = "local"
    engine_model: str = ""


@dataclass(slots=True)
class RetrievalMatch:
    record: ImportedRecord
    score: float
    overlap_tokens: list[str]
    tag_overlap_tokens: list[str]
    title_overlap_tokens: list[str]
    event_date: str
    ranking_reason: str


def ask_question(
    config: AppConfig,
    question: str,
    *,
    snapshot_scope: str = "all",
    days: int = 7,
    source_type: str | None = None,
    dry_run: bool = False,
    persist: bool = True,
    provider: AskProvider | None = None,
    provider_override: str | None = None,
) -> AskResult:
    if days <= 0:
        raise ValueError("--days must be a positive integer.")

    settings = load_project_settings(config)
    engine_mode = _effective_engine_mode(settings, provider_override)
    engine_model = resolve_task_model(settings, "ask")
    if provider is not None and not dry_run:
        engine_mode = "api"
        engine_model = getattr(provider, "model", "") or engine_model

    with get_connection(config.database_path) as connection:
        current_persona = get_current_persona_core_version(
            connection, snapshot_scope=snapshot_scope
        )
        if current_persona is None:
            return AskResult(
                status="empty",
                message=f"No persona core found for scope {snapshot_scope}. Run `pop persona rebuild` first.",
                persisted=False,
                engine_mode=engine_mode,
                engine_model=engine_model,
            )

        persona_core_version_id, persona_core = current_persona
        all_scope_snapshots = list_daily_persona_snapshots(connection, snapshot_scope=snapshot_scope)
        recent_snapshots = select_recent_snapshots(
            all_scope_snapshots,
            source_snapshot_ids=persona_core.source_snapshot_ids,
            days=days,
        )
        imported_records = list_imported_records(connection, source_type=source_type)
        retrieval_matches = retrieve_relevant_memories(
            question,
            imported_records,
            limit=5,
            source_type=source_type,
        )
        prompt_package = render_prompt_package(
            question=question,
            persona_core=persona_core,
            recent_snapshots=recent_snapshots,
            retrieval_matches=retrieval_matches,
        )

        selected_provider = provider
        if selected_provider is None and not dry_run:
            try:
                selected_provider = _provider_from_settings(
                    settings,
                    provider_override=provider_override,
                )
            except ProviderError as exc:
                if settings.fallback_to_local_on_error:
                    selected_provider = None
                    engine_mode = "local"
                    engine_model = ""
                else:
                    return AskResult(
                        status="error",
                        message=f"AI 提问分析失败：{exc}",
                        prompt_package=prompt_package,
                        persona_core=persona_core,
                        recent_snapshots=recent_snapshots,
                        retrieval_notes=[],
                        used_memory_ids=[],
                        persisted=False,
                        engine_mode=engine_mode,
                        engine_model=engine_model,
                    )

        response: str | None = None
        message = "Assembled persona-assisted prompt package in dry-run mode."
        if selected_provider is not None and not dry_run:
            try:
                response = selected_provider.answer(prompt_package)
                message = (
                    f"Assembled persona-assisted prompt package and called provider {selected_provider.name}."
                )
            except ProviderError as exc:
                if settings.fallback_to_local_on_error:
                    selected_provider = None
                    engine_mode = "local"
                    engine_model = ""
                    response = None
                    message = f"AI 提问分析失败，已回退到本地模式：{exc}"
                else:
                    return AskResult(
                        status="error",
                        message=f"AI 提问分析失败：{exc}",
                        prompt_package=prompt_package,
                        persona_core=persona_core,
                        recent_snapshots=recent_snapshots,
                        retrieval_notes=[],
                        used_memory_ids=[],
                        persisted=False,
                        engine_mode=engine_mode,
                        engine_model=engine_model,
                    )
        mode = "provider" if selected_provider is not None and not dry_run else "dry_run"

        retrieval_notes = [
            {
                "memory_id": match.record.id,
                "score": round(match.score, 3),
                "overlap_tokens": match.overlap_tokens,
                "tag_overlap_tokens": match.tag_overlap_tokens,
                "title_overlap_tokens": match.title_overlap_tokens,
                "event_date": match.event_date,
                "source_type": match.record.source_type,
                "ranking_reason": match.ranking_reason,
            }
            for match in retrieval_matches
        ]
        session: SessionRecord | None = None
        json_path: Path | None = None
        markdown_path: Path | None = None
        if persist:
            session_id = new_id("sess")
            json_path = config.sessions_dir / f"{session_id}.json"
            markdown_path = config.sessions_dir / f"{session_id}.md"
            session = SessionRecord(
                session_id=session_id,
                question=question,
                snapshot_scope=snapshot_scope,
                persona_core_version_id=persona_core_version_id,
                used_snapshot_ids=[snapshot.id for snapshot in recent_snapshots],
                used_memory_ids=[match.record.id for match in retrieval_matches],
                used_persona_fields=PERSONA_FIELDS.copy(),
                prompt_context=prompt_package,
                response=response,
                mode=mode,
                retrieval_notes=retrieval_notes,
                source_type_filter=source_type,
                recent_days=days,
                artifact_path=str(json_path),
                markdown_path=str(markdown_path),
                created_at=utc_now(),
            )
            write_json(json_path, session.model_dump(mode="json"))
            markdown_path.write_text(render_session_markdown(session), encoding="utf-8")
            insert_session_record(connection, session)
            ensure_audit_record(config, session_id, connection=connection)
            message = (
                message
                if selected_provider is not None and not dry_run
                else "Assembled persona-assisted prompt package in dry-run mode."
            )
        else:
            message = message or "Assembled persona-assisted prompt package without saving a session."

    return AskResult(
        status="created",
        message=message,
        session=session,
        prompt_package=prompt_package,
        persona_core=persona_core,
        recent_snapshots=recent_snapshots,
        retrieval_notes=retrieval_notes,
        used_memory_ids=[match.record.id for match in retrieval_matches],
        persisted=persist,
        json_path=json_path,
        markdown_path=markdown_path,
        engine_mode=engine_mode,
        engine_model=engine_model,
    )


def format_ask_result(result: AskResult) -> str:
    lines = [result.message]
    if result.session is None:
        return "\n".join(lines)
    lines.extend(
        [
            f"session_id: {result.session.session_id}",
            f"snapshot_scope: {result.session.snapshot_scope}",
            f"used_snapshots: {len(result.session.used_snapshot_ids)}",
            f"used_memories: {len(result.session.used_memory_ids)}",
            f"mode: {result.session.mode}",
        ]
    )
    if result.json_path is not None:
        lines.append(f"json: {result.json_path}")
    if result.markdown_path is not None:
        lines.append(f"markdown: {result.markdown_path}")
    return "\n".join(lines)


def select_recent_snapshots(
    snapshots: list[DailyPersonaSnapshot], *, source_snapshot_ids: list[str], days: int
) -> list[DailyPersonaSnapshot]:
    source_set = set(source_snapshot_ids)
    matching = [snapshot for snapshot in snapshots if snapshot.id in source_set]
    if not matching:
        return []
    ordered = sorted(
        matching,
        key=lambda snapshot: (snapshot.date_range.date_to, snapshot.created_at, snapshot.id),
    )
    latest_date = max(date.fromisoformat(snapshot.date_range.date_to) for snapshot in ordered)
    cutoff = latest_date.toordinal() - max(days - 1, 0)
    return [
        snapshot
        for snapshot in ordered
        if date.fromisoformat(snapshot.date_range.date_to).toordinal() >= cutoff
    ]


def retrieve_relevant_memories(
    question: str,
    records: list[ImportedRecord],
    *,
    limit: int = 5,
    source_type: str | None = None,
) -> list[RetrievalMatch]:
    question_tokens = tokenize_question(question)
    filtered_records = [
        record for record in records if source_type is None or record.source_type == source_type
    ]
    if not filtered_records:
        return []

    latest_event = max(resolve_effective_event_timestamp(record) for record in filtered_records)
    matches: list[RetrievalMatch] = []
    for record in filtered_records:
        match = score_record_against_question(
            question=question,
            question_tokens=question_tokens,
            record=record,
            latest_event=latest_event,
            source_type_filter=source_type,
        )
        if match is not None:
            matches.append(match)

    if matches:
        ordered = sorted(
            matches,
            key=lambda match: (
                -match.score,
                -resolve_effective_event_timestamp(match.record).timestamp(),
                match.record.id,
            ),
        )
        return ordered[:limit]

    fallback_records = sorted(
        filtered_records,
        key=lambda record: (-resolve_effective_event_timestamp(record).timestamp(), record.id),
    )[:limit]
    return [
        RetrievalMatch(
            record=record,
            score=0.0,
            overlap_tokens=[],
            tag_overlap_tokens=[],
            title_overlap_tokens=[],
            event_date=resolve_effective_event_timestamp(record).date().isoformat(),
            ranking_reason="fallback_recent_no_keyword_overlap",
        )
        for record in fallback_records
    ]


def score_record_against_question(
    *,
    question: str,
    question_tokens: list[str],
    record: ImportedRecord,
    latest_event,
    source_type_filter: str | None,
) -> RetrievalMatch | None:
    content_tokens = tokenize_searchable_text(record.content)
    tag_tokens = tokenize_searchable_text(" ".join(record.tags))
    title_tokens = tokenize_searchable_text(str(record.metadata.get("conversation_title", "")))
    overlap_tokens = sorted(set(question_tokens) & set(content_tokens))
    tag_overlap_tokens = sorted(set(question_tokens) & set(tag_tokens))
    title_overlap_tokens = sorted(set(question_tokens) & set(title_tokens))
    lexical_hits = len(overlap_tokens) + len(tag_overlap_tokens) + len(title_overlap_tokens)
    if lexical_hits == 0:
        return None

    searchable_text = " ".join(
        [
            record.content.lower(),
            " ".join(record.tags).lower(),
            str(record.metadata.get("conversation_title", "")).lower(),
        ]
    )
    phrase_bonus = 0.0
    normalized_question = normalize_whitespace(question).lower()
    if len(normalized_question) >= 18 and normalized_question in searchable_text:
        phrase_bonus = 4.0

    event_time = resolve_effective_event_timestamp(record)
    recency_days = max((latest_event.date() - event_time.date()).days, 0)
    recency_bonus = max(0.0, 2.0 - min(recency_days, 20) * 0.1)
    source_type_bonus = 1.0 if source_type_filter and record.source_type == source_type_filter else 0.0
    score = (
        len(overlap_tokens) * 10.0
        + len(tag_overlap_tokens) * 6.0
        + len(title_overlap_tokens) * 4.0
        + phrase_bonus
        + recency_bonus
        + source_type_bonus
    )
    reasons = []
    if overlap_tokens:
        reasons.append(f"content_overlap={','.join(overlap_tokens)}")
    if tag_overlap_tokens:
        reasons.append(f"tag_overlap={','.join(tag_overlap_tokens)}")
    if title_overlap_tokens:
        reasons.append(f"title_overlap={','.join(title_overlap_tokens)}")
    if phrase_bonus:
        reasons.append("question_phrase_match")
    if recency_bonus:
        reasons.append(f"recency_bonus={round(recency_bonus, 2)}")
    if source_type_bonus:
        reasons.append(f"source_type_match={record.source_type}")

    return RetrievalMatch(
        record=record,
        score=score,
        overlap_tokens=overlap_tokens,
        tag_overlap_tokens=tag_overlap_tokens,
        title_overlap_tokens=title_overlap_tokens,
        event_date=event_time.date().isoformat(),
        ranking_reason="; ".join(reasons),
    )


def render_prompt_package(
    *,
    question: str,
    persona_core: PersonaCore,
    recent_snapshots: list[DailyPersonaSnapshot],
    retrieval_matches: list[RetrievalMatch],
) -> str:
    sections = [
        "# Persona-Assisted Prompt Package",
        "",
        "## Persona Core Summary",
        render_persona_core_context(persona_core),
        "",
        "## Recent Daily Context",
        render_recent_snapshot_context(recent_snapshots),
        "",
        "## Relevant Memory Excerpts",
        render_memory_context(retrieval_matches),
        "",
        "## Current Question",
        question,
        "",
        "## Answer Guidance",
        "- Answer consistently with the persona core while staying grounded in the retrieved evidence.",
        "- Prefer stable traits over one-off recent signals when they conflict.",
        "- Use recent shifts as short-term context, not as a replacement for long-term patterns.",
        "- If retrieved evidence is thin, state that explicitly instead of over-claiming.",
    ]
    return "\n".join(sections).strip() + "\n"


def render_persona_core_context(persona_core: PersonaCore) -> str:
    lines = [
        f"- Scope: {persona_core.snapshot_scope}",
        f"- Identity: {persona_core.identity}",
        f"- Long-term goals: {', '.join(persona_core.long_term_goals) if persona_core.long_term_goals else 'None detected'}",
        f"- Current focus: {', '.join(persona_core.current_focus) if persona_core.current_focus else 'None detected'}",
        f"- Decision style: {persona_core.decision_style or 'No clear pattern detected.'}",
        f"- Risk profile: {persona_core.risk_profile or 'No clear pattern detected.'}",
        f"- Stable biases: {', '.join(persona_core.stable_biases) if persona_core.stable_biases else 'None detected'}",
        f"- Recurring topics: {', '.join(persona_core.recurring_topics) if persona_core.recurring_topics else 'None detected'}",
        f"- Expression style: {', '.join(persona_core.expression_style) if persona_core.expression_style else 'None detected'}",
        f"- Boundaries: {', '.join(persona_core.taboos_and_boundaries) if persona_core.taboos_and_boundaries else 'None detected'}",
        f"- Recent shifts: {', '.join(persona_core.recent_shifts) if persona_core.recent_shifts else 'None detected'}",
        f"- Confidence notes: {' | '.join(persona_core.confidence_notes) if persona_core.confidence_notes else 'None'}",
    ]
    return "\n".join(lines)


def render_recent_snapshot_context(recent_snapshots: list[DailyPersonaSnapshot]) -> str:
    if not recent_snapshots:
        return "- No recent daily snapshots available for this scope."
    lines: list[str] = []
    for snapshot in recent_snapshots:
        focus = ", ".join(snapshot.current_focus[:2]) if snapshot.current_focus else "None detected"
        goals = ", ".join(snapshot.goal_priority[:2]) if snapshot.goal_priority else "None detected"
        shifts = ", ".join(snapshot.new_traits[:2]) if snapshot.new_traits else "None detected"
        lines.append(
            f"- {snapshot.date_range.date_from}: goals={goals}; focus={focus}; new_traits={shifts}"
        )
    return "\n".join(lines)


def render_memory_context(retrieval_matches: list[RetrievalMatch]) -> str:
    if not retrieval_matches:
        return "- No relevant memories matched the question."
    lines: list[str] = []
    for index, match in enumerate(retrieval_matches, start=1):
        title = match.record.metadata.get("conversation_title") or "Untitled"
        excerpt = excerpt_text(match.record.content, max_chars=220)
        lines.append(
            "\n".join(
                [
                    (
                        f"{index}. memory_id={match.record.id} score={round(match.score, 3)} "
                        f"source_type={match.record.source_type} event_date={match.event_date}"
                    ),
                    f"   title={title}",
                    f"   reason={match.ranking_reason}",
                    f"   excerpt={excerpt}",
                ]
            )
        )
    return "\n".join(lines)


def render_session_markdown(session: SessionRecord) -> str:
    sections = [
        "# Persona Session",
        "",
        f"- Session ID: {session.session_id}",
        f"- Scope: {session.snapshot_scope}",
        f"- Persona Core Version ID: {session.persona_core_version_id or 'None'}",
        f"- Created At: {session.created_at.isoformat()}",
        f"- Mode: {session.mode}",
        f"- Source Type Filter: {session.source_type_filter or 'None'}",
        f"- Recent Days: {session.recent_days}",
        f"- Feedback Status: {session.feedback_status}",
        f"- Feedback Updated At: {session.feedback_updated_at.isoformat() if session.feedback_updated_at else 'Not reviewed'}",
        f"- Used Snapshot IDs: {', '.join(session.used_snapshot_ids) if session.used_snapshot_ids else 'None'}",
        f"- Used Memory IDs: {', '.join(session.used_memory_ids) if session.used_memory_ids else 'None'}",
        "",
        "## Question",
        session.question,
        "",
        "## Prompt Package",
        "```text",
        session.prompt_context.rstrip(),
        "```",
        "",
        "## Retrieval Notes",
        _render_retrieval_notes(session.retrieval_notes),
        "",
        "## Feedback Note",
        session.feedback_note or "No feedback note yet.",
        "",
        "## Response",
        session.response or "Dry-run only. No provider response.",
    ]
    return "\n".join(sections).strip() + "\n"


def tokenize_question(question: str) -> list[str]:
    tokens = tokenize_searchable_text(question)
    return [token for token in tokens if token not in QUESTION_STOPWORDS]


def tokenize_searchable_text(value: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9\\-]{1,}", value.lower())


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def excerpt_text(value: str, *, max_chars: int) -> str:
    text = normalize_whitespace(value)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars].rstrip()}..."


def _render_retrieval_notes(notes: list[dict[str, Any]]) -> str:
    if not notes:
        return "- No retrieval notes recorded."
    return "\n".join(
        f"- {note['memory_id']}: score={note['score']} reason={note['ranking_reason']}"
        for note in notes
    )


def _provider_from_settings(settings, *, provider_override: str | None) -> AskProvider | None:
    effective_mode = _effective_engine_mode(settings, provider_override)
    if effective_mode == "local":
        return None

    model = resolve_task_model(settings, "ask")
    if not model:
        if effective_mode == "api" and not settings.fallback_to_local_on_error:
            raise ProviderError("还没有配置提问分析模型。")
        return None
    if not settings.api_base_url.strip() or not settings.api_key.strip():
        if effective_mode == "api" and not settings.fallback_to_local_on_error:
            raise ProviderError("API 地址或 API 密钥还没有配置。")
        return None
    return OpenAICompatibleAskProvider(
        client=build_provider_client(settings),
        model=model,
    )


def _effective_engine_mode(settings, provider_override: str | None) -> str:
    if provider_override in {"local", "api"}:
        return provider_override
    return settings.provider_mode
