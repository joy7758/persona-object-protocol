from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from pydantic import ValidationError

from pop_cockpit.audit import list_audit_entries, load_audit_entry
from pop_cockpit.browser_capture import capture_status, run_capture_self_test
from pop_cockpit.chatgpt_importer import import_chatgpt_export
from pop_cockpit.config import AppConfig
from pop_cockpit.execution import (
    approve_and_run_execution_intent,
    get_execution_detail,
    list_execution_items,
    parse_execution_parameters,
    propose_execution_intent,
    reject_execution_intent,
    review_execution_intent,
    simulate_execution_intent,
)
from pop_cockpit.importer import import_folder_to_workspace
from pop_cockpit.injector import AskResult, ask_question, render_session_markdown
from pop_cockpit.llm_api import (
    ProviderError,
    mask_api_key,
    provider_status_text,
    resolve_task_model,
    test_provider_connection,
)
from pop_cockpit.persona import (
    export_persona_core,
    export_persona_package,
    rebuild_persona_core,
    show_persona_core,
)
from pop_cockpit.scheduler import (
    SchedulerResult,
    disable_scheduler,
    enable_scheduler,
    install_scheduler,
    scheduler_status,
)
from pop_cockpit.settings import load_project_settings, save_project_settings
from pop_cockpit.storage import (
    get_connection,
    get_current_persona_core,
    get_current_persona_core_version,
    get_session_record,
    list_available_snapshot_scopes,
    list_daily_persona_snapshots,
    list_imported_records,
    list_session_records,
    update_session_feedback,
)
from pop_cockpit.sync import (
    export_persona_sync_package,
    get_sync_status,
    import_remote_packages,
    initialize_sync,
    pause_sync,
    resume_sync,
    run_sync_now,
    set_sync_passphrase,
)
from pop_cockpit.workflow import run_daily_workflow
from pop_cockpit.utils import utc_now, write_json


@dataclass(slots=True)
class UploadActionResult:
    status: str
    message: str
    payload: Any | None = None


FEEDBACK_STATUS_LABELS = {
    "accepted": "采纳",
    "partial": "部分采纳",
    "rejected": "不采纳",
    "not_reviewed": "未评价",
}

REVIEW_STATUS_LABELS = {
    "approved": "批准",
    "rejected": "已拒绝",
    "useful": "有用",
    "not_useful": "没用",
    "pending": "待处理",
}

EXECUTION_STATUS_LABELS = {
    "proposed": "已提出",
    "approved": "已确认",
    "simulated": "已预演",
    "rejected": "已丢弃",
    "failed": "失败",
}

TARGET_TYPE_LABELS = {
    "software_tool": "软件工具",
    "local_script": "本地脚本",
    "simulated_device": "模拟设备",
    "robotic_carrier": "机器人载体",
}

MODE_LABELS = {
    "dry_run": "仅整理上下文",
    "provider": "已调用模型",
}

SOURCE_TYPE_LABELS = {
    "text": "文本",
    "markdown": "Markdown 笔记",
    "json": "JSON 记录",
    "chatgpt_export": "ChatGPT 导出历史",
    "chatgpt_browser_capture": "ChatGPT 网页自动记录",
}

SAFETY_LEVEL_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
}

EXECUTION_MODE_LABELS = {
    "simulation": "模拟预演",
    "approved_simulation": "确认后预演",
}

PROVIDER_MODE_LABELS = {
    "local": "本地模式",
    "api": "API 模式",
    "hybrid": "混合模式",
}

PROVIDER_TEST_STATUS_LABELS = {
    "not_tested": "未测试",
    "success": "连接成功",
    "failed": "连接失败",
}

SYNC_HEALTH_LABELS = {
    "healthy": "健康",
    "paused": "已暂停",
    "issue": "需要处理",
}


def scope_label(scope: str) -> str:
    if scope == "all":
        return "全部"
    if scope.startswith("source_type:"):
        source_type = scope.split(":", 1)[1]
        return SOURCE_TYPE_LABELS.get(source_type, f"来源：{source_type}")
    return scope


def labeled_options(values: list[str], labels: dict[str, str] | None = None) -> list[dict[str, str]]:
    mapping = labels or {}
    return [{"value": value, "label": mapping.get(value, value)} for value in values]


async def import_uploaded_notes(config: AppConfig, uploads: list[UploadFile]) -> UploadActionResult:
    valid_uploads = [upload for upload in uploads if upload.filename]
    if not valid_uploads:
        return UploadActionResult(status="empty", message="还没有选择要导入的文件。")

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        for upload in valid_uploads:
            target_path = temp_dir / Path(upload.filename or "upload").name
            target_path.write_bytes(await upload.read())
        summary = import_folder_to_workspace(config, temp_dir)

    return UploadActionResult(
        status="completed",
        message=f"已导入 {summary.imported_count} 个文件到 POP。",
        payload=summary,
    )


async def import_uploaded_chatgpt_export_file(
    config: AppConfig, upload: UploadFile | None
) -> UploadActionResult:
    if upload is None or not upload.filename:
        return UploadActionResult(status="empty", message="还没有选择 ChatGPT 导出包。")

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        temp_path = temp_dir / Path(upload.filename).name
        temp_path.write_bytes(await upload.read())
        summary = import_chatgpt_export(config, temp_path)

    return UploadActionResult(
        status="completed",
        message=f"已导入 {summary.imported_messages} 条 ChatGPT 历史消息。",
        payload=summary,
    )


def run_dashboard_workflow(config: AppConfig) -> UploadActionResult:
    result = run_daily_workflow(config, command_name="daily")
    message = result.message
    if result.status == "completed":
        workflow_date = result.run_record.workflow_date if result.run_record else "today"
        message = f"POP 已完成 {workflow_date} 的画像更新。"
    elif result.status == "missing_config":
        message = "还没有设置收件箱目录，请先去设置页完成配置。"
    return UploadActionResult(status=result.status, message=message, payload=result)


def run_capture_test_from_web(config: AppConfig) -> UploadActionResult:
    result = run_capture_self_test(config)
    if result.status == "imported":
        message = "测试采集成功，POP 已收到一条自检消息。"
    elif result.status == "duplicate":
        message = "测试采集已到达后端，但这条自检消息之前已经存在。"
    else:
        message = f"测试采集失败：{result.reason or '暂时无法写入采集消息。'}"
    return UploadActionResult(status=result.status, message=message, payload=result)


def rebuild_persona_for_scope(config: AppConfig, scope: str) -> UploadActionResult:
    result = rebuild_persona_core(config, snapshot_scope=scope)
    message = result.message
    if result.status == "created":
        message = f"已更新「{scope_label(scope)}」这组视图的人格画像。"
    elif result.status == "empty":
        message = f"「{scope_label(scope)}」这组视图还没有可用的每日快照。"
    elif result.status == "error":
        message = f"人格重建失败：{result.message}"
    return UploadActionResult(status=result.status, message=message, payload=result)


def ask_from_web(
    config: AppConfig,
    *,
    question: str,
    scope: str,
    days: int,
    source_type: str | None,
    save_session: bool,
    provider_override: str | None = None,
) -> AskResult:
    result = ask_question(
        config,
        question,
        snapshot_scope=scope,
        days=days,
        source_type=source_type,
        dry_run=not save_session,
        persist=save_session,
        provider_override=provider_override,
    )
    if result.status == "created":
        result.message = (
            (
                "已完成分析并保存这次结果。"
                if result.session and result.session.response
                else "已整理好上下文，并保存这次分析。"
            )
            if save_session
            else "已整理好上下文，但还没有保存成新的分析记录。"
        )
    elif result.status == "empty":
        result.message = f"还没有找到「{scope_label(scope)}」这组视图的人格画像，请先更新。"
    elif result.status == "error":
        result.message = result.message or "AI 分析暂时不可用。"
    return result


def install_scheduler_from_web(
    config: AppConfig, *, inbox_path: str, hour: int, minute: int
) -> SchedulerResult:
    if not inbox_path.strip():
        return SchedulerResult(
            status="error",
            message="请先保存收件箱目录，再安装自动更新。",
        )
    result = install_scheduler(config, hour=hour, minute=minute, inbox_path=Path(inbox_path))
    if result.status == "installed":
        result.message = "已安装自动更新任务，请再点一次“开启自动更新”。"
    elif result.status == "error":
        result.message = "安装自动更新失败，请检查本地环境后重试。"
    return result


def save_daily_settings_from_web(
    config: AppConfig,
    *,
    inbox_path: str,
    archive_path: str,
    failed_path: str,
    archive_after_import: bool,
) -> UploadActionResult:
    if not inbox_path.strip():
        return UploadActionResult(status="error", message="请先填写收件箱目录。")
    settings = load_project_settings(config)
    settings.inbox_path = inbox_path.strip()
    settings.archive_path = archive_path.strip()
    settings.failed_path = failed_path.strip()
    settings.archive_after_import = archive_after_import
    save_project_settings(config, settings)
    return UploadActionResult(
        status="saved",
        message="已保存每日收件目录和归档设置。",
        payload=settings,
    )


def save_provider_settings_from_web(
    config: AppConfig,
    *,
    provider_mode: str,
    api_base_url: str,
    api_key: str,
    default_model: str,
    extract_model: str,
    persona_model: str,
    ask_model: str,
    fallback_to_local_on_error: bool,
) -> UploadActionResult:
    settings = load_project_settings(config)
    settings.provider_mode = provider_mode
    settings.api_base_url = api_base_url.strip()
    submitted_api_key = api_key.strip()
    if submitted_api_key:
        settings.api_key = submitted_api_key
    settings.default_model = default_model.strip()
    settings.extract_model = extract_model.strip()
    settings.persona_model = persona_model.strip()
    settings.ask_model = ask_model.strip()
    settings.fallback_to_local_on_error = fallback_to_local_on_error
    save_project_settings(config, settings)
    return UploadActionResult(
        status="saved",
        message="已保存 AI 接口设置。",
        payload=settings,
    )


def test_provider_from_web(
    config: AppConfig,
    *,
    provider_mode: str,
    api_base_url: str,
    api_key: str,
    default_model: str,
    extract_model: str,
    persona_model: str,
    ask_model: str,
    fallback_to_local_on_error: bool,
) -> UploadActionResult:
    settings = load_project_settings(config)
    settings.provider_mode = provider_mode
    settings.api_base_url = api_base_url.strip()
    submitted_api_key = api_key.strip()
    if submitted_api_key:
        settings.api_key = submitted_api_key
    settings.default_model = default_model.strip()
    settings.extract_model = extract_model.strip()
    settings.persona_model = persona_model.strip()
    settings.ask_model = ask_model.strip()
    settings.fallback_to_local_on_error = fallback_to_local_on_error

    if provider_mode == "local":
        settings.last_provider_test_at = utc_now()
        settings.last_provider_test_status = "not_tested"
        settings.last_provider_test_message = "当前处于本地模式，不需要测试外部接口。"
        save_project_settings(config, settings)
        return UploadActionResult(
            status="success",
            message=settings.last_provider_test_message,
            payload=settings,
        )

    try:
        result = test_provider_connection(settings)
        settings.last_provider_test_at = result.checked_at
        settings.last_provider_test_status = "success"
        settings.last_provider_test_message = result.message
        save_project_settings(config, settings)
        return UploadActionResult(status="success", message=result.message, payload=settings)
    except ProviderError as exc:
        settings.last_provider_test_at = utc_now()
        settings.last_provider_test_status = "failed"
        settings.last_provider_test_message = str(exc)
        save_project_settings(config, settings)
        return UploadActionResult(
            status="error",
            message=f"连接测试失败：{exc}",
            payload=settings,
        )


def get_dashboard_context(config: AppConfig) -> dict[str, Any]:
    scheduler = scheduler_status(config)
    capture = capture_status(config)
    settings = load_project_settings(config)
    latest_workflow = load_latest_workflow_run(config)
    with get_connection(config.database_path) as connection:
        imports = list_imported_records(connection)
        snapshots = list_daily_persona_snapshots(connection, snapshot_scope="all")
        current_persona = get_current_persona_core_version(connection, snapshot_scope="all")
        recent_sessions = list_session_records(connection, limit=40)
    recent_intents, _recent_results = list_execution_items(config, limit=40)
    latest_snapshot = snapshots[-1] if snapshots else None
    recent_import_count = sum(
        1
        for record in imports
        if record.imported_at >= utc_now() - timedelta(days=1)
    )
    recent_cutoff = utc_now() - timedelta(days=7)
    recent_analysis_count = sum(
        1 for session in recent_sessions if session.created_at >= recent_cutoff
    )
    recent_action_draft_count = sum(
        1 for intent in recent_intents if intent.created_at >= recent_cutoff
    )
    feedback_summary = {
        "accepted": sum(1 for session in recent_sessions if session.feedback_status == "accepted"),
        "partial": sum(1 for session in recent_sessions if session.feedback_status == "partial"),
        "rejected": sum(1 for session in recent_sessions if session.feedback_status == "rejected"),
        "not_reviewed": sum(
            1 for session in recent_sessions if session.feedback_status == "not_reviewed"
        ),
        "useful_actions": sum(
            1 for intent in recent_intents if intent.review_status == "useful"
        ),
        "pending_actions": sum(
            1 for intent in recent_intents if intent.review_status == "pending"
        ),
        "not_useful_actions": sum(
            1 for intent in recent_intents if intent.review_status == "not_useful"
        ),
    }
    today_label = utc_now().date().isoformat()
    latest_persona_updated = (
        current_persona[1].last_updated.isoformat()
        if current_persona is not None and current_persona[1].last_updated is not None
        else None
    )
    provider_summary = {
        "mode": settings.provider_mode,
        "mode_label": PROVIDER_MODE_LABELS.get(settings.provider_mode, settings.provider_mode),
        "default_model": settings.default_model or "未设置",
        "status_label": provider_status_text(settings),
        "last_test_at": (
            settings.last_provider_test_at.isoformat()
            if settings.last_provider_test_at is not None
            else "未测试"
        ),
    }
    capture_working = bool(
        capture.capture_endpoint_available
        and capture.extension_connected
        and capture.last_capture_status != "error"
        and capture.last_capture_at
    )
    if not capture.capture_endpoint_available or not capture.backend_alive:
        capture_hint = "POP 后端没有正常运行，请先执行：pop start"
    elif not capture.extension_connected:
        capture_hint = "请打开 Chrome 插件，并确认“自动记录”已经开启。"
    elif capture.last_capture_status == "error":
        capture_hint = capture.last_error_message or "网页自动记录失败，请再试一次。"
    elif not capture.last_capture_at:
        capture_hint = "还没有收到网页消息，请先刷新 ChatGPT 页面。"
    elif capture.recent_captured_count == 0:
        capture_hint = "最近 10 分钟没有新消息，试着刷新 ChatGPT 页面。"
    else:
        capture_hint = "网页自动记录正在工作，你可以正常聊天。"
    capture_summary = {
        "working": capture_working,
        "status_label": "工作中" if capture_working else "未工作",
        "last_capture_at": capture.last_capture_at or "还没有记录",
        "last_error": capture.last_error_message or "无",
        "recent_count": capture.recent_captured_count,
        "extension_connected_label": "已连接" if capture.extension_connected else "未连接",
        "hint": capture_hint,
        "last_extension_heartbeat_at": capture.last_extension_heartbeat_at or "还没有心跳",
    }
    sync_status = get_sync_status(config)
    sync_summary = {
        "health": sync_status.health,
        "status_label": SYNC_HEALTH_LABELS.get(sync_status.health, sync_status.health),
        "last_sync_time": sync_status.last_sync_time or "还没有同步",
        "role": sync_status.device_role,
        "enabled_label": "已开启" if sync_status.enabled else "已暂停",
    }
    return {
        "scheduler": scheduler,
        "latest_workflow": latest_workflow,
        "latest_persona_updated": latest_persona_updated,
        "recent_import_count": recent_import_count,
        "recent_analysis_count": recent_analysis_count,
        "recent_action_draft_count": recent_action_draft_count,
        "feedback_summary": feedback_summary,
        "latest_snapshot": latest_snapshot,
        "today_updated": bool(
            latest_workflow and latest_workflow.get("workflow_date") == today_label
        ),
        "capture_status": capture,
        "capture_summary": capture_summary,
        "sync_status": sync_status,
        "sync_summary": sync_summary,
        "scopes": get_available_scopes(config),
        "settings": settings,
        "provider_summary": provider_summary,
    }


def get_import_page_context(config: AppConfig) -> dict[str, Any]:
    return {
        "recent_imports": get_recent_imports(config, limit=12),
        "source_type_labels": SOURCE_TYPE_LABELS,
    }


def get_persona_page_context(config: AppConfig, *, scope: str) -> dict[str, Any]:
    persona_result = show_persona_core(config, snapshot_scope=scope)
    if persona_result.status == "empty":
        persona_result.message = f"「{scope_label(scope)}」这组视图还没有生成人格画像。"
    return {
        "scope": scope,
        "scopes": get_available_scopes(config),
        "scope_options": labeled_options(get_available_scopes(config), {
            option: scope_label(option) for option in get_available_scopes(config)
        }),
        "persona_result": persona_result,
        "import_package_message": "人格包导入会在后续阶段开放，现在已经可以先导出。",
    }


def get_ask_page_context(
    config: AppConfig,
    *,
    question: str = "",
    scope: str,
    days: int,
    source_type: str | None,
    ask_result: AskResult | None = None,
    provider_override: str = "default",
) -> dict[str, Any]:
    settings = load_project_settings(config)
    current_engine_mode = (
        ask_result.engine_mode
        if ask_result is not None and ask_result.engine_mode
        else (provider_override if provider_override in {"local", "api"} else settings.provider_mode)
    )
    current_engine_model = (
        ask_result.engine_model
        if ask_result is not None and ask_result.engine_model is not None
        else resolve_task_model(settings, "ask")
    )
    current_engine_model_label = (
        "本地模式无需模型"
        if current_engine_mode == "local"
        else (current_engine_model or "未设置")
    )
    return {
        "question": question,
        "scope": scope,
        "scopes": get_available_scopes(config),
        "scope_options": labeled_options(get_available_scopes(config), {
            option: scope_label(option) for option in get_available_scopes(config)
        }),
        "days": days,
        "source_type": source_type or "",
        "ask_result": ask_result,
        "provider_override": provider_override,
        "provider_override_options": [
            {"value": "default", "label": "跟随默认设置"},
            {"value": "local", "label": "临时使用本地模式"},
            {"value": "api", "label": "临时使用 API 模式"},
        ],
        "current_engine_mode": current_engine_mode,
        "current_engine_mode_label": PROVIDER_MODE_LABELS.get(current_engine_mode, current_engine_mode),
        "current_engine_model": current_engine_model_label,
        "feedback_status_options": labeled_options(
            ["accepted", "partial", "rejected", "not_reviewed"],
            FEEDBACK_STATUS_LABELS,
        ),
        "feedback_status_labels": FEEDBACK_STATUS_LABELS,
        "scope_labels": {option: scope_label(option) for option in get_available_scopes(config)},
    }


def get_audit_page_context(
    config: AppConfig,
    *,
    scope: str | None,
    mode: str | None,
    limit: int,
    session_id: str | None = None,
) -> dict[str, Any]:
    audits = list_audit_entries(config, snapshot_scope=scope, mode=mode, limit=limit)
    selected_audit = None
    selected_session = None
    if session_id:
        selected = load_audit_entry(config, session_id)
        selected_audit = selected.audit_record
    elif audits:
        selected_audit = audits[0]
    if selected_audit is not None:
        with get_connection(config.database_path) as connection:
            selected_session = get_session_record(connection, selected_audit.session_id)
    return {
        "audits": audits,
        "selected_audit": selected_audit,
        "selected_session": selected_session,
        "scope": scope or "",
        "mode": mode or "",
        "limit": limit,
        "scopes": get_available_scopes(config),
        "scope_options": labeled_options(get_available_scopes(config), {
            option: scope_label(option) for option in get_available_scopes(config)
        }),
        "feedback_status_options": labeled_options(
            ["accepted", "partial", "rejected", "not_reviewed"],
            FEEDBACK_STATUS_LABELS,
        ),
        "feedback_status_labels": FEEDBACK_STATUS_LABELS,
        "mode_labels": MODE_LABELS,
        "scope_labels": {option: scope_label(option) for option in get_available_scopes(config)},
    }


def get_settings_page_context(config: AppConfig) -> dict[str, Any]:
    settings = load_project_settings(config)
    scheduler = scheduler_status(config)
    scheduler_config = settings.scheduler
    sync_status = get_sync_status(config)
    return {
        "settings": settings,
        "scheduler": scheduler,
        "scheduler_hour": scheduler_config.hour if scheduler_config is not None else 22,
        "scheduler_minute": scheduler_config.minute if scheduler_config is not None else 30,
        "inbox_path": settings.inbox_path,
        "archive_path": settings.archive_path,
        "failed_path": settings.failed_path,
        "archive_after_import": settings.archive_after_import,
        "provider_mode": settings.provider_mode,
        "provider_mode_options": labeled_options(
            ["local", "api", "hybrid"],
            PROVIDER_MODE_LABELS,
        ),
        "api_base_url": settings.api_base_url,
        "masked_api_key": mask_api_key(settings.api_key),
        "default_model": settings.default_model,
        "extract_model": settings.extract_model,
        "persona_model": settings.persona_model,
        "ask_model": settings.ask_model,
        "fallback_to_local_on_error": settings.fallback_to_local_on_error,
        "last_provider_test_at": (
            settings.last_provider_test_at.isoformat()
            if settings.last_provider_test_at is not None
            else ""
        ),
        "last_provider_test_status": settings.last_provider_test_status,
        "last_provider_test_status_label": provider_status_text(settings),
        "last_provider_test_message": settings.last_provider_test_message,
        "sync_status": sync_status,
        "sync_health_label": SYNC_HEALTH_LABELS.get(sync_status.health, sync_status.health),
    }


def get_sync_page_context(config: AppConfig) -> dict[str, Any]:
    sync_status = get_sync_status(config)
    return {
        "sync_status": sync_status,
        "sync_health_label": SYNC_HEALTH_LABELS.get(sync_status.health, sync_status.health),
    }


def get_execution_page_context(
    config: AppConfig,
    *,
    intent_id: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    intents, results = list_execution_items(config, limit=limit)
    selected_intent_id = intent_id or (intents[0].intent_id if intents else None)
    selected_detail = (
        get_execution_detail(config, selected_intent_id)
        if selected_intent_id is not None
        else None
    )
    with get_connection(config.database_path) as connection:
        sessions = list_session_records(connection, limit=12)
    return {
        "execution_intents": intents,
        "execution_results": results,
        "selected_detail": selected_detail,
        "selected_intent_id": selected_intent_id or "",
        "available_sessions": sessions,
        "scopes": get_available_scopes(config),
        "scope_options": labeled_options(get_available_scopes(config), {
            option: scope_label(option) for option in get_available_scopes(config)
        }),
        "target_type_options": labeled_options(
            [
                "software_tool",
                "local_script",
                "simulated_device",
                "robotic_carrier",
            ],
            TARGET_TYPE_LABELS,
        ),
        "safety_level_options": labeled_options(["low", "medium", "high"], SAFETY_LEVEL_LABELS),
        "review_status_options": labeled_options(
            ["approved", "rejected", "useful", "not_useful", "pending"],
            REVIEW_STATUS_LABELS,
        ),
        "review_status_labels": REVIEW_STATUS_LABELS,
        "execution_status_labels": EXECUTION_STATUS_LABELS,
        "target_type_labels": TARGET_TYPE_LABELS,
        "safety_level_labels": SAFETY_LEVEL_LABELS,
        "execution_mode_labels": EXECUTION_MODE_LABELS,
        "scope_labels": {option: scope_label(option) for option in get_available_scopes(config)},
        "limit": limit,
    }


def save_sync_settings_from_web(
    config: AppConfig,
    *,
    sync_root_path: str,
    device_role: str,
    device_name: str,
    sync_interval_seconds: int,
    sync_auto_start: bool,
) -> UploadActionResult:
    root_value = sync_root_path.strip()
    if not root_value:
        return UploadActionResult(status="error", message="请先填写同步目录。")
    if device_role not in {"primary", "secondary"}:
        return UploadActionResult(status="error", message="设备角色必须是 primary 或 secondary。")
    if sync_interval_seconds <= 0:
        return UploadActionResult(status="error", message="同步间隔必须大于 0 秒。")

    result = initialize_sync(
        config,
        root_path=root_value,
        role=device_role,
        device_name=device_name.strip(),
        provider="google_drive_folder",
    )
    if result.status == "error":
        return UploadActionResult(status="error", message=result.message)
    settings = load_project_settings(config)
    settings.sync_interval_seconds = sync_interval_seconds
    settings.sync_auto_start = sync_auto_start
    save_project_settings(config, settings)
    return UploadActionResult(status=result.status, message="已保存同步目录和设备角色设置。")


def set_sync_passphrase_from_web(config: AppConfig, *, sync_passphrase: str) -> UploadActionResult:
    result = set_sync_passphrase(config, sync_passphrase)
    if result.status == "error":
        return UploadActionResult(status="error", message=result.message)
    return UploadActionResult(status="saved", message="已更新本机同步密钥。")


def run_sync_now_from_web(config: AppConfig) -> UploadActionResult:
    result = run_sync_now(config)
    if result.status == "error":
        return UploadActionResult(status="error", message=result.message)
    return UploadActionResult(status=result.status, message="已完成一次安全同步。", payload=result.payload)


def pause_sync_from_web(config: AppConfig) -> UploadActionResult:
    result = pause_sync(config)
    return UploadActionResult(status=result.status, message="已暂停这台设备的自动同步。")


def resume_sync_from_web(config: AppConfig) -> UploadActionResult:
    result = resume_sync(config)
    return UploadActionResult(status=result.status, message="已恢复这台设备的自动同步。")


def export_persona_sync_from_web(config: AppConfig) -> UploadActionResult:
    result = export_persona_sync_package(config, force=True)
    if result.status == "error":
        return UploadActionResult(status="error", message=result.message)
    return UploadActionResult(status=result.status, message=result.message, payload=result.payload)


def import_remote_sync_from_web(config: AppConfig) -> UploadActionResult:
    result = import_remote_packages(config)
    if result.status == "error":
        return UploadActionResult(status="error", message=result.message)
    return UploadActionResult(status=result.status, message=result.message, payload=result.payload)


def propose_execution_from_web(
    config: AppConfig,
    *,
    source_session_id: str | None,
    action_type: str,
    target_type: str,
    target_name: str,
    parameters_text: str,
    rationale: str,
    safety_level: str,
    requires_confirmation: bool,
    snapshot_scope: str,
) -> UploadActionResult:
    try:
        parameters = parse_execution_parameters(parameters_text)
        result = propose_execution_intent(
            config,
            source_session_id=source_session_id or None,
            action_type=action_type,
            target_type=target_type,
            target_name=target_name,
            parameters=parameters,
            rationale=rationale,
            requires_confirmation=requires_confirmation,
            safety_level=safety_level,
            snapshot_scope=snapshot_scope,
        )
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        return UploadActionResult(status="error", message=f"参数格式有误：{exc}")
    message = result.message
    if result.status == "created":
        message = "已创建新的动作草案。"
    elif result.status == "existing":
        message = "这条动作草案已经存在。"
    elif result.status == "missing":
        message = "没有找到对应的已保存分析，暂时无法生成动作草案。"
    return UploadActionResult(status=result.status, message=message, payload=result)


def simulate_execution_from_web(config: AppConfig, intent_id: str) -> UploadActionResult:
    result = simulate_execution_intent(config, intent_id)
    message = result.message
    if result.status == "simulated":
        message = "已在本地完成这条动作草案的预演。"
    elif result.status == "rejected":
        message = "这条动作草案已经被丢弃，不能继续预演。"
    elif result.status == "missing":
        message = "没有找到这条动作草案。"
    elif result.status == "failed":
        message = "这次预演失败了，请检查草案内容后再试。"
    return UploadActionResult(status=result.status, message=message, payload=result)


def approve_execution_from_web(config: AppConfig, intent_id: str) -> UploadActionResult:
    result = approve_and_run_execution_intent(config, intent_id)
    message = result.message
    if result.status == "simulated":
        message = "已确认这条草案，并在本地完成预演。"
    elif result.status == "missing":
        message = "没有找到这条动作草案。"
    elif result.status == "rejected":
        message = "这条动作草案已经被丢弃，不能再确认。"
    return UploadActionResult(status=result.status, message=message, payload=result)


def reject_execution_from_web(config: AppConfig, intent_id: str) -> UploadActionResult:
    result = reject_execution_intent(config, intent_id)
    message = result.message
    if result.status == "rejected":
        message = "已丢弃这条动作草案。"
    elif result.status == "missing":
        message = "没有找到这条动作草案。"
    return UploadActionResult(status=result.status, message=message, payload=result)


def review_execution_from_web(
    config: AppConfig,
    *,
    intent_id: str,
    review_status: str,
    review_note: str,
) -> UploadActionResult:
    result = review_execution_intent(
        config,
        intent_id,
        review_status=review_status,
        review_note=review_note,
    )
    message = result.message
    if result.status == "reviewed":
        message = "已保存你对这条草案的反馈。"
    elif result.status == "missing":
        message = "没有找到这条动作草案。"
    return UploadActionResult(status=result.status, message=message, payload=result)


def save_session_feedback_from_web(
    config: AppConfig,
    *,
    session_id: str,
    feedback_status: str,
    feedback_note: str,
) -> UploadActionResult:
    with get_connection(config.database_path) as connection:
        session = get_session_record(connection, session_id)
        if session is None:
            return UploadActionResult(
                status="missing",
                message=f"没有找到编号为 {session_id} 的已保存分析。",
            )
        now = utc_now()
        session.feedback_status = feedback_status
        session.feedback_note = feedback_note.strip()
        session.feedback_updated_at = now
        update_session_feedback(
            connection,
            session_id,
            feedback_status=feedback_status,
            feedback_note=session.feedback_note,
            feedback_updated_at=now.isoformat(),
        )
        if session.artifact_path:
            write_json(Path(session.artifact_path), session.model_dump(mode="json"))
        if session.markdown_path:
            Path(session.markdown_path).write_text(
                render_session_markdown(session),
                encoding="utf-8",
            )
    return UploadActionResult(
        status="updated",
        message="已保存你对这次分析的反馈。",
        payload=session,
    )


def load_saved_ask_result(config: AppConfig, session_id: str) -> AskResult | None:
    settings = load_project_settings(config)
    with get_connection(config.database_path) as connection:
        session = get_session_record(connection, session_id)
        if session is None:
            return None
        persona_core = get_current_persona_core(connection, snapshot_scope=session.snapshot_scope)
        snapshots = [
            snapshot
            for snapshot in list_daily_persona_snapshots(
                connection,
                snapshot_scope=session.snapshot_scope,
            )
            if snapshot.id in set(session.used_snapshot_ids)
        ]
    return AskResult(
        status="loaded",
        message="已加载这次已保存分析。",
        session=session,
        prompt_package=session.prompt_context,
        persona_core=persona_core,
        recent_snapshots=snapshots,
        retrieval_notes=session.retrieval_notes,
        used_memory_ids=session.used_memory_ids,
        persisted=True,
        json_path=Path(session.artifact_path) if session.artifact_path else None,
        markdown_path=Path(session.markdown_path) if session.markdown_path else None,
        engine_mode="api" if session.mode == "provider" else "local",
        engine_model=resolve_task_model(settings, "ask"),
    )


def get_recent_imports(config: AppConfig, *, limit: int) -> list[dict[str, Any]]:
    with get_connection(config.database_path) as connection:
        records = list_imported_records(connection)
    ordered = sorted(records, key=lambda record: (record.imported_at, record.id), reverse=True)
    return [
        {
            "id": record.id,
            "source_type": record.source_type,
            "source_type_label": SOURCE_TYPE_LABELS.get(record.source_type, record.source_type),
            "imported_at": record.imported_at.isoformat(),
            "source_path": record.source_path,
            "content_excerpt": _excerpt(record.content, 180),
        }
        for record in ordered[:limit]
    ]


def get_available_scopes(config: AppConfig) -> list[str]:
    with get_connection(config.database_path) as connection:
        return list_available_snapshot_scopes(connection)


def load_latest_workflow_run(config: AppConfig) -> dict[str, Any] | None:
    candidates = sorted(config.logs_dir.glob("workflow_run_*.json"))
    if not candidates:
        return None
    payload = json.loads(candidates[-1].read_text(encoding="utf-8"))
    return payload


def export_persona_file(config: AppConfig, *, scope: str) -> Path | None:
    result = export_persona_core(config, snapshot_scope=scope)
    return result.json_path


def export_persona_markdown_file(config: AppConfig, *, scope: str) -> Path | None:
    result = export_persona_core(config, snapshot_scope=scope)
    return result.markdown_path


def export_persona_package_file(config: AppConfig, *, scope: str) -> Path | None:
    result = export_persona_package(config, snapshot_scope=scope)
    return result.package_path


def enable_scheduler_from_web(config: AppConfig) -> SchedulerResult:
    result = enable_scheduler(config)
    if result.status == "enabled":
        result.message = "已开启自动更新。"
    elif result.status == "missing":
        result.message = "还没有安装自动更新任务，请先安装。"
    elif result.status == "error":
        result.message = "开启自动更新失败，请检查本地权限后重试。"
    return result


def disable_scheduler_from_web(config: AppConfig) -> SchedulerResult:
    result = disable_scheduler(config)
    if result.status == "disabled":
        result.message = "已关闭自动更新。"
    elif result.status == "error":
        result.message = "关闭自动更新失败，请稍后再试。"
    return result


def _excerpt(value: str, max_chars: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars].rstrip()}..."
