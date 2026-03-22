from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class DateRange(BaseModel):
    date_from: str
    date_to: str


class ImportedRecord(BaseModel):
    id: str
    source_type: str
    source_path: str
    imported_at: datetime
    content: str
    content_hash: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DailyExtractionRequest(BaseModel):
    date_range: DateRange
    records: list[ImportedRecord] = Field(default_factory=list)
    prompt: str = ""


class DailyPersonaSnapshotDraft(BaseModel):
    date_range: DateRange
    source_record_ids: list[str] = Field(default_factory=list)
    goal_priority: list[str] = Field(default_factory=list)
    current_focus: list[str] = Field(default_factory=list)
    decision_style: str = ""
    risk_profile: str = ""
    recurring_topics: list[str] = Field(default_factory=list)
    stable_biases: list[str] = Field(default_factory=list)
    emotional_signals: list[str] = Field(default_factory=list)
    new_traits: list[str] = Field(default_factory=list)
    important_decisions: list[str] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)
    provider_name: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class DailyPersonaSnapshot(DailyPersonaSnapshotDraft):
    id: str
    created_at: datetime


class ChatGPTConversationMetadata(BaseModel):
    conversation_id: str
    conversation_title: str = ""
    source_path: str
    imported_at: datetime
    message_count: int = 0
    message_ids: list[str] = Field(default_factory=list)
    first_message_at: str | None = None
    last_message_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonaCore(BaseModel):
    identity: str = ""
    long_term_goals: list[str] = Field(default_factory=list)
    current_focus: list[str] = Field(default_factory=list)
    decision_style: str = ""
    risk_profile: str = ""
    stable_biases: list[str] = Field(default_factory=list)
    recurring_topics: list[str] = Field(default_factory=list)
    expression_style: list[str] = Field(default_factory=list)
    taboos_and_boundaries: list[str] = Field(default_factory=list)
    recent_shifts: list[str] = Field(default_factory=list)
    evidence_summary: list[str] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)
    source_snapshot_ids: list[str] = Field(default_factory=list)
    snapshot_scope: str = "all"
    last_updated: datetime | None = None


class SessionRecord(BaseModel):
    session_id: str
    question: str
    snapshot_scope: str = "all"
    persona_core_version_id: str | None = None
    used_snapshot_ids: list[str] = Field(default_factory=list)
    used_memory_ids: list[str] = Field(default_factory=list)
    used_persona_fields: list[str] = Field(default_factory=list)
    prompt_context: str = ""
    response: str | None = None
    mode: str = "dry_run"
    retrieval_notes: list[dict[str, Any]] = Field(default_factory=list)
    source_type_filter: str | None = None
    recent_days: int = 7
    artifact_path: str = ""
    markdown_path: str = ""
    feedback_status: Literal["accepted", "partial", "rejected", "not_reviewed"] = "not_reviewed"
    feedback_note: str = ""
    feedback_updated_at: datetime | None = None
    created_at: datetime


class AuditRecord(BaseModel):
    audit_id: str
    session_id: str
    created_at: datetime
    snapshot_scope: str = "all"
    mode: str = "dry_run"
    question: str
    persona_core_version_id: str | None = None
    used_snapshot_ids: list[str] = Field(default_factory=list)
    used_memory_ids: list[str] = Field(default_factory=list)
    used_persona_fields: list[str] = Field(default_factory=list)
    retrieval_notes: list[dict[str, Any]] = Field(default_factory=list)
    prompt_context_hash: str = ""
    response_hash: str | None = None
    prompt_context_excerpt: str = ""
    prompt_context_path: str = ""
    response_present: bool = False
    artifact_path: str = ""
    markdown_path: str = ""


class SchedulerConfig(BaseModel):
    label: str = "com.zhangbin.pop-persona-cockpit.daily"
    hour: int = 22
    minute: int = 30
    inbox_path: str = ""
    plist_path: str = ""
    command_path: str = ""
    command_args: list[str] = Field(default_factory=list)
    stdout_log_path: str = ""
    stderr_log_path: str = ""


ProviderMode = Literal["local", "api", "hybrid"]
ProviderTestStatus = Literal["not_tested", "success", "failed"]
SyncProvider = Literal["google_drive_folder"]
DeviceRole = Literal["primary", "secondary"]


class ProjectSettings(BaseModel):
    inbox_path: str = ""
    archive_path: str = ""
    failed_path: str = ""
    archive_after_import: bool = False
    auto_open_browser: bool = True
    scheduler: SchedulerConfig | None = None
    provider_mode: ProviderMode = "local"
    api_base_url: str = ""
    api_key: str = ""
    default_model: str = ""
    extract_model: str = ""
    persona_model: str = ""
    ask_model: str = ""
    fallback_to_local_on_error: bool = True
    last_provider_test_at: datetime | None = None
    last_provider_test_status: ProviderTestStatus = "not_tested"
    last_provider_test_message: str = ""
    sync_enabled: bool = False
    sync_provider: SyncProvider = "google_drive_folder"
    sync_root_path: str = ""
    device_id: str = ""
    device_name: str = ""
    device_role: DeviceRole = "secondary"
    sync_interval_seconds: int = 60
    sync_passphrase_set: bool = False
    sync_auto_start: bool = False
    sync_snapshot_days: int = 30


class WorkflowRunRecord(BaseModel):
    run_id: str
    command_name: str
    created_at: datetime
    workflow_date: str
    inbox_path: str
    imported_count: int = 0
    skipped_count: int = 0
    duplicate_count: int = 0
    unsupported_count: int = 0
    archived_count: int = 0
    failed_moved_count: int = 0
    daily_snapshot_status: str = ""
    daily_snapshot_id: str | None = None
    persona_rebuild_status: str = ""
    persona_core_scope: str = "all"
    artifact_path: str = ""
    log_path: str = ""


class BrowserCaptureMessage(BaseModel):
    role: str
    text: str
    page_url: str
    conversation_title: str = ""
    captured_at: datetime
    message_fingerprint: str
    dom_index: int | None = None


class BrowserCaptureIngestionResult(BaseModel):
    status: str
    imported: bool = False
    duplicate: bool = False
    skipped: bool = False
    reason: str = ""
    record_id: str | None = None
    source_type: str = "chatgpt_browser_capture"


class CaptureEventRecord(BaseModel):
    timestamp: str
    role: str = "unknown"
    preview: str = ""
    status: str = "idle"
    message_fingerprint: str = ""
    record_id: str | None = None
    reason: str = ""


class CaptureStatusResponse(BaseModel):
    status: str = "ok"
    backend_alive: bool = True
    capture_endpoint_available: bool = True
    backend_url: str = "http://127.0.0.1:8765"
    extension_connected: bool = False
    last_extension_heartbeat_at: str | None = None
    last_capture_at: str | None = None
    last_capture_status: str = "idle"
    last_error_message: str = ""
    recent_captured_count: int = 0
    expected_frontend_origin: list[str] = Field(default_factory=list)
    browser_captured_count_recent: int = 0
    latest_browser_capture_at: str | None = None


ExecutionIntentStatus = Literal["proposed", "approved", "simulated", "rejected", "failed"]
ExecutionSafetyLevel = Literal["low", "medium", "high"]
ExecutionAdapterType = Literal[
    "software_tool",
    "local_script",
    "simulated_device",
    "robotic_carrier",
]
ExecutionMode = Literal["simulation", "approved_simulation"]


class ExecutionIntent(BaseModel):
    intent_id: str
    created_at: datetime
    source_session_id: str | None = None
    source_audit_id: str | None = None
    action_type: str
    target_type: ExecutionAdapterType
    target_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    requires_confirmation: bool = True
    safety_level: ExecutionSafetyLevel = "medium"
    status: ExecutionIntentStatus = "proposed"
    review_status: Literal["approved", "rejected", "useful", "not_useful", "pending"] = "pending"
    review_note: str = ""
    review_updated_at: datetime | None = None
    snapshot_scope: str = "all"
    persona_core_version_id: str | None = None


class ExecutionResult(BaseModel):
    result_id: str
    intent_id: str
    created_at: datetime
    adapter_type: ExecutionAdapterType
    execution_mode: ExecutionMode
    success: bool
    output_text: str = ""
    output_data: dict[str, Any] = Field(default_factory=dict)
    error_text: str | None = None
