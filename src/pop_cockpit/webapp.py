from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pop_cockpit.browser_capture import (
    browser_capture_endpoint_contract,
    capture_status,
    ingest_browser_capture_message,
    list_recent_capture_events,
    record_extension_heartbeat,
)
from pop_cockpit.config import AppConfig
from pop_cockpit.execution import get_execution_detail, list_execution_items
from pop_cockpit.schemas import BrowserCaptureMessage
from pop_cockpit.storage import ensure_runtime
from pop_cockpit.web_services import (
    approve_execution_from_web,
    ask_from_web,
    disable_scheduler_from_web,
    enable_scheduler_from_web,
    export_persona_file,
    export_persona_markdown_file,
    export_persona_package_file,
    export_persona_sync_from_web,
    get_ask_page_context,
    get_audit_page_context,
    get_dashboard_context,
    get_execution_page_context,
    get_import_page_context,
    get_persona_page_context,
    get_settings_page_context,
    get_sync_page_context,
    import_remote_sync_from_web,
    import_uploaded_chatgpt_export_file,
    import_uploaded_notes,
    install_scheduler_from_web,
    load_saved_ask_result,
    pause_sync_from_web,
    propose_execution_from_web,
    reject_execution_from_web,
    rebuild_persona_for_scope,
    run_capture_test_from_web,
    resume_sync_from_web,
    review_execution_from_web,
    run_sync_now_from_web,
    run_dashboard_workflow,
    save_daily_settings_from_web,
    save_provider_settings_from_web,
    save_session_feedback_from_web,
    save_sync_settings_from_web,
    set_sync_passphrase_from_web,
    simulate_execution_from_web,
    test_provider_from_web,
)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(config: AppConfig | None = None) -> FastAPI:
    app = FastAPI(
        title="POP Persona Cockpit",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.pop_config = config or AppConfig.load()
    ensure_runtime(app.state.pop_config)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    def render(
        request: Request,
        template_name: str,
        page_title: str,
        context: dict | None = None,
        *,
        notice: str = "",
        error: str = "",
    ) -> HTMLResponse:
        base_context = {
            "request": request,
            "page_title": page_title,
            "notice": notice,
            "error": error,
            "nav_items": [
                {"href": "/", "label": "首页"},
                {"href": "/imports", "label": "导入"},
                {"href": "/persona", "label": "我的数字人格"},
                {"href": "/ask", "label": "提问分析"},
                {"href": "/execution", "label": "动作草案"},
                {"href": "/audit", "label": "分析依据"},
                {"href": "/sync", "label": "同步"},
                {"href": "/settings", "label": "设置"},
            ],
        }
        if context:
            base_context.update(context)
        return templates.TemplateResponse(request, template_name, base_context)

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        return render(
            request,
            "dashboard.html",
            "首页",
            get_dashboard_context(app.state.pop_config),
        )

    @app.post("/dashboard/run-daily", response_class=HTMLResponse)
    def dashboard_run_daily(request: Request) -> HTMLResponse:
        action_result = run_dashboard_workflow(app.state.pop_config)
        context = get_dashboard_context(app.state.pop_config)
        context["workflow_result"] = action_result.payload
        return render(
            request,
            "dashboard.html",
            "首页",
            context,
            notice=action_result.message,
        )

    @app.post("/dashboard/test-capture", response_class=HTMLResponse)
    def dashboard_test_capture(request: Request) -> HTMLResponse:
        action_result = run_capture_test_from_web(app.state.pop_config)
        context = get_dashboard_context(app.state.pop_config)
        return render(
            request,
            "dashboard.html",
            "首页",
            context,
            notice=action_result.message if action_result.status != "error" else "",
            error=action_result.message if action_result.status == "error" else "",
        )

    @app.post("/dashboard/sync-now", response_class=HTMLResponse)
    def dashboard_sync_now(request: Request) -> HTMLResponse:
        action_result = run_sync_now_from_web(app.state.pop_config)
        context = get_dashboard_context(app.state.pop_config)
        return render(
            request,
            "dashboard.html",
            "首页",
            context,
            notice=action_result.message if action_result.status != "error" else "",
            error=action_result.message if action_result.status == "error" else "",
        )

    @app.get("/imports", response_class=HTMLResponse)
    def imports_page(request: Request) -> HTMLResponse:
        return render(
            request,
            "imports.html",
            "导入",
            get_import_page_context(app.state.pop_config),
        )

    @app.post("/imports/files", response_class=HTMLResponse)
    async def imports_upload_files(
        request: Request,
        files: list[UploadFile] | None = File(default=None),
    ) -> HTMLResponse:
        action_result = await import_uploaded_notes(app.state.pop_config, files or [])
        return render(
            request,
            "imports.html",
            "导入",
            get_import_page_context(app.state.pop_config),
            notice=action_result.message,
        )

    @app.post("/imports/chatgpt-export", response_class=HTMLResponse)
    async def imports_upload_chatgpt_export(
        request: Request,
        chatgpt_export: UploadFile | None = File(default=None),
    ) -> HTMLResponse:
        action_result = await import_uploaded_chatgpt_export_file(
            app.state.pop_config,
            chatgpt_export,
        )
        return render(
            request,
            "imports.html",
            "导入",
            get_import_page_context(app.state.pop_config),
            notice=action_result.message,
        )

    @app.get("/persona", response_class=HTMLResponse)
    def persona_page(request: Request, scope: str = "all") -> HTMLResponse:
        return render(
            request,
            "persona.html",
            "我的数字人格",
            get_persona_page_context(app.state.pop_config, scope=scope),
        )

    @app.post("/persona/rebuild", response_class=HTMLResponse)
    def persona_rebuild_page(
        request: Request,
        scope: str = Form("all"),
    ) -> HTMLResponse:
        result = rebuild_persona_for_scope(app.state.pop_config, scope)
        context = get_persona_page_context(app.state.pop_config, scope=scope)
        context["persona_action_result"] = result.payload
        return render(
            request,
            "persona.html",
            "我的数字人格",
            context,
            notice=result.message,
        )

    @app.get("/persona/export/json")
    def persona_export_json(scope: str = "all") -> FileResponse:
        export_path = export_persona_file(app.state.pop_config, scope=scope)
        if export_path is None:
            raise HTTPException(status_code=404, detail="Persona core export failed.")
        return FileResponse(export_path, filename=export_path.name, media_type="application/json")

    @app.get("/persona/export/markdown")
    def persona_export_markdown(scope: str = "all") -> FileResponse:
        export_path = export_persona_markdown_file(app.state.pop_config, scope=scope)
        if export_path is None:
            raise HTTPException(status_code=404, detail="Persona core export failed.")
        return FileResponse(export_path, filename=export_path.name, media_type="text/markdown")

    @app.get("/persona/export/package")
    def persona_export_package(scope: str = "all") -> FileResponse:
        export_path = export_persona_package_file(app.state.pop_config, scope=scope)
        if export_path is None:
            raise HTTPException(status_code=404, detail="Persona package export failed.")
        return FileResponse(export_path, filename=export_path.name, media_type="application/zip")

    @app.get("/ask", response_class=HTMLResponse)
    def ask_page(
        request: Request,
        question: str = "",
        scope: str = "all",
        days: int = 7,
        source_type: str = "",
        provider_override: str = "default",
    ) -> HTMLResponse:
        return render(
            request,
            "ask.html",
            "提问分析",
            get_ask_page_context(
                app.state.pop_config,
                question=question,
                scope=scope,
                days=days,
                source_type=source_type or None,
                provider_override=provider_override,
            ),
        )

    @app.post("/ask", response_class=HTMLResponse)
    def ask_submit(
        request: Request,
        question: str = Form(...),
        scope: str = Form("all"),
        days: int = Form(7),
        source_type: str = Form(""),
        action: str = Form("assemble"),
        provider_override: str = Form("default"),
    ) -> HTMLResponse:
        ask_result = ask_from_web(
            app.state.pop_config,
            question=question,
            scope=scope,
            days=days,
            source_type=source_type or None,
            save_session=action == "save",
            provider_override=provider_override,
        )
        context = get_ask_page_context(
            app.state.pop_config,
            question=question,
            scope=scope,
            days=days,
            source_type=source_type or None,
            ask_result=ask_result,
            provider_override=provider_override,
        )
        return render(
            request,
            "ask.html",
            "提问分析",
            context,
            notice=ask_result.message if ask_result.status != "error" else "",
            error=ask_result.message if ask_result.status == "error" else "",
        )

    @app.post("/ask/{session_id}/feedback", response_class=HTMLResponse)
    def ask_feedback(
        request: Request,
        session_id: str,
        feedback_status: str = Form(...),
        feedback_note: str = Form(""),
    ) -> HTMLResponse:
        result = save_session_feedback_from_web(
            app.state.pop_config,
            session_id=session_id,
            feedback_status=feedback_status,
            feedback_note=feedback_note,
        )
        ask_result = load_saved_ask_result(app.state.pop_config, session_id)
        scope = ask_result.session.snapshot_scope if ask_result and ask_result.session else "all"
        days = ask_result.session.recent_days if ask_result and ask_result.session else 7
        source_type = (
            ask_result.session.source_type_filter
            if ask_result and ask_result.session
            else None
        )
        question = ask_result.session.question if ask_result and ask_result.session else ""
        return render(
            request,
            "ask.html",
            "提问分析",
            get_ask_page_context(
                app.state.pop_config,
                question=question,
                scope=scope,
                days=days,
                source_type=source_type,
                ask_result=ask_result,
                provider_override="default",
            ),
            notice=result.message if result.status != "missing" else "",
            error=result.message if result.status == "missing" else "",
        )

    @app.get("/audit", response_class=HTMLResponse)
    def audit_page(
        request: Request,
        scope: str = "",
        mode: str = "",
        limit: int = 20,
        session_id: str = "",
    ) -> HTMLResponse:
        return render(
            request,
            "audit.html",
            "分析依据",
            get_audit_page_context(
                app.state.pop_config,
                scope=scope or None,
                mode=mode or None,
                limit=limit,
                session_id=session_id or None,
            ),
        )

    @app.get("/audit/{session_id}", response_class=HTMLResponse)
    def audit_detail(request: Request, session_id: str, scope: str = "", mode: str = "", limit: int = 20) -> HTMLResponse:
        return render(
            request,
            "audit.html",
            "分析依据",
            get_audit_page_context(
                app.state.pop_config,
                scope=scope or None,
                mode=mode or None,
                limit=limit,
                session_id=session_id,
            ),
        )

    @app.post("/audit/{session_id}/feedback", response_class=HTMLResponse)
    def audit_feedback(
        request: Request,
        session_id: str,
        feedback_status: str = Form(...),
        feedback_note: str = Form(""),
        scope: str = Form(""),
        mode: str = Form(""),
        limit: int = Form(20),
    ) -> HTMLResponse:
        result = save_session_feedback_from_web(
            app.state.pop_config,
            session_id=session_id,
            feedback_status=feedback_status,
            feedback_note=feedback_note,
        )
        return render(
            request,
            "audit.html",
            "分析依据",
            get_audit_page_context(
                app.state.pop_config,
                scope=scope or None,
                mode=mode or None,
                limit=limit,
                session_id=session_id,
            ),
            notice=result.message if result.status != "missing" else "",
            error=result.message if result.status == "missing" else "",
        )

    @app.get("/execution", response_class=HTMLResponse)
    def execution_page(
        request: Request,
        intent_id: str = "",
        limit: int = 20,
    ) -> HTMLResponse:
        return render(
            request,
            "execution.html",
            "动作草案",
            get_execution_page_context(
                app.state.pop_config,
                intent_id=intent_id or None,
                limit=limit,
            ),
        )

    @app.post("/execution/propose", response_class=HTMLResponse)
    def execution_propose(
        request: Request,
        source_session_id: str = Form(""),
        snapshot_scope: str = Form("all"),
        action_type: str = Form(...),
        target_type: str = Form(...),
        target_name: str = Form(...),
        parameters_text: str = Form(""),
        rationale: str = Form(""),
        safety_level: str = Form("medium"),
        requires_confirmation: bool = Form(True),
    ) -> HTMLResponse:
        result = propose_execution_from_web(
            app.state.pop_config,
            source_session_id=source_session_id or None,
            action_type=action_type,
            target_type=target_type,
            target_name=target_name,
            parameters_text=parameters_text,
            rationale=rationale,
            safety_level=safety_level,
            requires_confirmation=requires_confirmation,
            snapshot_scope=snapshot_scope,
        )
        selected_intent_id = (
            result.payload.intent.intent_id
            if result.payload is not None and result.payload.intent is not None
            else ""
        )
        return render(
            request,
            "execution.html",
            "动作草案",
            get_execution_page_context(
                app.state.pop_config,
                intent_id=selected_intent_id or None,
            ),
            notice=result.message if result.status != "error" else "",
            error=result.message if result.status == "error" else "",
        )

    @app.post("/execution/{intent_id}/simulate", response_class=HTMLResponse)
    def execution_simulate(request: Request, intent_id: str) -> HTMLResponse:
        result = simulate_execution_from_web(app.state.pop_config, intent_id)
        return render(
            request,
            "execution.html",
            "动作草案",
            get_execution_page_context(app.state.pop_config, intent_id=intent_id),
            notice=result.message if result.status != "missing" else "",
            error=result.message if result.status == "missing" else "",
        )

    @app.post("/execution/{intent_id}/approve", response_class=HTMLResponse)
    def execution_approve(request: Request, intent_id: str) -> HTMLResponse:
        result = approve_execution_from_web(app.state.pop_config, intent_id)
        return render(
            request,
            "execution.html",
            "动作草案",
            get_execution_page_context(app.state.pop_config, intent_id=intent_id),
            notice=result.message if result.status not in {"missing", "rejected"} else "",
            error=result.message if result.status in {"missing", "rejected"} else "",
        )

    @app.post("/execution/{intent_id}/reject", response_class=HTMLResponse)
    def execution_reject(request: Request, intent_id: str) -> HTMLResponse:
        result = reject_execution_from_web(app.state.pop_config, intent_id)
        return render(
            request,
            "execution.html",
            "动作草案",
            get_execution_page_context(app.state.pop_config, intent_id=intent_id),
            notice=result.message if result.status != "missing" else "",
            error=result.message if result.status == "missing" else "",
        )

    @app.post("/execution/{intent_id}/review", response_class=HTMLResponse)
    def execution_review(
        request: Request,
        intent_id: str,
        review_status: str = Form(...),
        review_note: str = Form(""),
    ) -> HTMLResponse:
        result = review_execution_from_web(
            app.state.pop_config,
            intent_id=intent_id,
            review_status=review_status,
            review_note=review_note,
        )
        return render(
            request,
            "execution.html",
            "动作草案",
            get_execution_page_context(app.state.pop_config, intent_id=intent_id),
            notice=result.message if result.status != "missing" else "",
            error=result.message if result.status == "missing" else "",
        )

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request) -> HTMLResponse:
        return render(
            request,
            "settings.html",
            "设置",
            get_settings_page_context(app.state.pop_config),
        )

    @app.post("/settings/sync/save", response_class=HTMLResponse)
    def settings_save_sync(
        request: Request,
        sync_root_path: str = Form(""),
        device_role: str = Form("secondary"),
        device_name: str = Form(""),
        sync_interval_seconds: int = Form(60),
        sync_auto_start: bool = Form(False),
    ) -> HTMLResponse:
        result = save_sync_settings_from_web(
            app.state.pop_config,
            sync_root_path=sync_root_path,
            device_role=device_role,
            device_name=device_name,
            sync_interval_seconds=sync_interval_seconds,
            sync_auto_start=sync_auto_start,
        )
        return render(
            request,
            "settings.html",
            "设置",
            get_settings_page_context(app.state.pop_config),
            notice=result.message if result.status != "error" else "",
            error=result.message if result.status == "error" else "",
        )

    @app.post("/settings/sync/passphrase", response_class=HTMLResponse)
    def settings_save_sync_passphrase(
        request: Request,
        sync_passphrase: str = Form(""),
    ) -> HTMLResponse:
        result = set_sync_passphrase_from_web(
            app.state.pop_config,
            sync_passphrase=sync_passphrase,
        )
        return render(
            request,
            "settings.html",
            "设置",
            get_settings_page_context(app.state.pop_config),
            notice=result.message if result.status != "error" else "",
            error=result.message if result.status == "error" else "",
        )
        

    @app.post("/settings/preferences", response_class=HTMLResponse)
    def settings_save_preferences(
        request: Request,
        inbox_path: str = Form(""),
        archive_path: str = Form(""),
        failed_path: str = Form(""),
        archive_after_import: bool = Form(False),
    ) -> HTMLResponse:
        result = save_daily_settings_from_web(
            app.state.pop_config,
            inbox_path=inbox_path,
            archive_path=archive_path,
            failed_path=failed_path,
            archive_after_import=archive_after_import,
        )
        return render(
            request,
            "settings.html",
            "设置",
            get_settings_page_context(app.state.pop_config),
            notice=result.message if result.status != "error" else "",
            error=result.message if result.status == "error" else "",
        )

    @app.post("/settings/provider/save", response_class=HTMLResponse)
    def settings_save_provider(
        request: Request,
        provider_mode: str = Form("local"),
        api_base_url: str = Form(""),
        api_key: str = Form(""),
        default_model: str = Form(""),
        extract_model: str = Form(""),
        persona_model: str = Form(""),
        ask_model: str = Form(""),
        fallback_to_local_on_error: bool = Form(False),
    ) -> HTMLResponse:
        result = save_provider_settings_from_web(
            app.state.pop_config,
            provider_mode=provider_mode,
            api_base_url=api_base_url,
            api_key=api_key,
            default_model=default_model,
            extract_model=extract_model,
            persona_model=persona_model,
            ask_model=ask_model,
            fallback_to_local_on_error=fallback_to_local_on_error,
        )
        return render(
            request,
            "settings.html",
            "设置",
            get_settings_page_context(app.state.pop_config),
            notice=result.message,
        )

    @app.post("/settings/provider/test", response_class=HTMLResponse)
    def settings_test_provider(
        request: Request,
        provider_mode: str = Form("local"),
        api_base_url: str = Form(""),
        api_key: str = Form(""),
        default_model: str = Form(""),
        extract_model: str = Form(""),
        persona_model: str = Form(""),
        ask_model: str = Form(""),
        fallback_to_local_on_error: bool = Form(False),
    ) -> HTMLResponse:
        result = test_provider_from_web(
            app.state.pop_config,
            provider_mode=provider_mode,
            api_base_url=api_base_url,
            api_key=api_key,
            default_model=default_model,
            extract_model=extract_model,
            persona_model=persona_model,
            ask_model=ask_model,
            fallback_to_local_on_error=fallback_to_local_on_error,
        )
        return render(
            request,
            "settings.html",
            "设置",
            get_settings_page_context(app.state.pop_config),
            notice=result.message if result.status != "error" else "",
            error=result.message if result.status == "error" else "",
        )

    @app.post("/settings/scheduler/install", response_class=HTMLResponse)
    def settings_install_scheduler(
        request: Request,
        inbox_path: str = Form(...),
        hour: int = Form(...),
        minute: int = Form(...),
    ) -> HTMLResponse:
        result = install_scheduler_from_web(
            app.state.pop_config,
            inbox_path=inbox_path,
            hour=hour,
            minute=minute,
        )
        return render(
            request,
            "settings.html",
            "设置",
            get_settings_page_context(app.state.pop_config),
            notice=result.message if result.status != "error" else "",
            error=result.message if result.status == "error" else "",
        )

    @app.post("/settings/scheduler/enable", response_class=HTMLResponse)
    def settings_enable_scheduler(request: Request) -> HTMLResponse:
        result = enable_scheduler_from_web(app.state.pop_config)
        return render(
            request,
            "settings.html",
            "设置",
            get_settings_page_context(app.state.pop_config),
            notice=result.message if result.status != "error" else "",
            error=result.message if result.status == "error" else "",
        )

    @app.post("/settings/scheduler/disable", response_class=HTMLResponse)
    def settings_disable_scheduler(request: Request) -> HTMLResponse:
        result = disable_scheduler_from_web(app.state.pop_config)
        return render(
            request,
            "settings.html",
            "设置",
            get_settings_page_context(app.state.pop_config),
            notice=result.message if result.status != "error" else "",
            error=result.message if result.status == "error" else "",
        )

    @app.get("/sync", response_class=HTMLResponse)
    def sync_page(request: Request) -> HTMLResponse:
        return render(
            request,
            "sync.html",
            "同步",
            get_sync_page_context(app.state.pop_config),
        )

    @app.post("/sync/now", response_class=HTMLResponse)
    def sync_now_page(request: Request) -> HTMLResponse:
        result = run_sync_now_from_web(app.state.pop_config)
        return render(
            request,
            "sync.html",
            "同步",
            get_sync_page_context(app.state.pop_config),
            notice=result.message if result.status != "error" else "",
            error=result.message if result.status == "error" else "",
        )

    @app.post("/sync/pause", response_class=HTMLResponse)
    def sync_pause_page(request: Request) -> HTMLResponse:
        result = pause_sync_from_web(app.state.pop_config)
        return render(
            request,
            "sync.html",
            "同步",
            get_sync_page_context(app.state.pop_config),
            notice=result.message,
        )

    @app.post("/sync/resume", response_class=HTMLResponse)
    def sync_resume_page(request: Request) -> HTMLResponse:
        result = resume_sync_from_web(app.state.pop_config)
        return render(
            request,
            "sync.html",
            "同步",
            get_sync_page_context(app.state.pop_config),
            notice=result.message,
        )

    @app.post("/sync/export-persona", response_class=HTMLResponse)
    def sync_export_persona_page(request: Request) -> HTMLResponse:
        result = export_persona_sync_from_web(app.state.pop_config)
        return render(
            request,
            "sync.html",
            "同步",
            get_sync_page_context(app.state.pop_config),
            notice=result.message if result.status != "error" else "",
            error=result.message if result.status == "error" else "",
        )

    @app.post("/sync/import-remote", response_class=HTMLResponse)
    def sync_import_remote_page(request: Request) -> HTMLResponse:
        result = import_remote_sync_from_web(app.state.pop_config)
        return render(
            request,
            "sync.html",
            "同步",
            get_sync_page_context(app.state.pop_config),
            notice=result.message if result.status != "error" else "",
            error=result.message if result.status == "error" else "",
        )

    @app.get("/api/capture/status")
    def capture_status_endpoint(source: str = "web") -> dict:
        if source == "extension":
            record_extension_heartbeat()
        status = capture_status(app.state.pop_config)
        payload = status.model_dump(mode="json")
        payload["contract"] = browser_capture_endpoint_contract()
        return payload

    @app.post("/api/capture/chat-message")
    def capture_chat_message(payload: BrowserCaptureMessage) -> dict:
        result = ingest_browser_capture_message(app.state.pop_config, payload)
        return result.model_dump(mode="json")

    @app.get("/api/capture/recent")
    def capture_recent_events(limit: int = 20) -> dict:
        events = list_recent_capture_events(limit=limit)
        return {
            "events": [event.model_dump(mode="json") for event in events],
            "count": len(events),
        }

    @app.post("/api/capture/test")
    def capture_test_endpoint() -> dict:
        result = run_capture_test_from_web(app.state.pop_config)
        payload = result.payload.model_dump(mode="json") if result.payload is not None else None
        return {
            "status": result.status,
            "message": result.message,
            "result": payload,
        }

    @app.get("/api/execution/list")
    def execution_list_api(limit: int = 20) -> dict:
        intents, results = list_execution_items(app.state.pop_config, limit=limit)
        return {
            "intents": [intent.model_dump(mode="json") for intent in intents],
            "results": [result.model_dump(mode="json") for result in results],
        }

    @app.get("/api/execution/{intent_id}")
    def execution_detail_api(intent_id: str) -> dict:
        detail = get_execution_detail(app.state.pop_config, intent_id)
        if detail.intent is None:
            raise HTTPException(status_code=404, detail="Execution intent not found.")
        return {
            "intent": detail.intent.model_dump(mode="json"),
            "results": [result.model_dump(mode="json") for result in detail.results],
        }

    return app


def run_web_server(config: AppConfig) -> None:
    app = create_app(config)
    uvicorn.run(app, host="127.0.0.1", port=8765)
