from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pop_cockpit.audit import ensure_audit_record
from pop_cockpit.config import AppConfig
from pop_cockpit.schemas import ExecutionIntent, ExecutionResult
from pop_cockpit.storage import (
    find_execution_intent_by_key,
    get_audit_record,
    get_connection,
    get_current_persona_core_version,
    get_execution_intent,
    get_session_record,
    insert_execution_intent,
    insert_execution_result,
    list_execution_intents,
    list_execution_results,
    update_execution_intent,
)
from pop_cockpit.utils import new_id, sha256_text, utc_now, write_json


@dataclass(slots=True)
class ExecutionOperationResult:
    status: str
    message: str
    intent: ExecutionIntent | None = None
    result: ExecutionResult | None = None
    intent_artifact_path: Path | None = None
    result_artifact_path: Path | None = None


@dataclass(slots=True)
class ExecutionDetail:
    intent: ExecutionIntent | None
    results: list[ExecutionResult]


class ExecutionAdapter:
    adapter_type: str = "software_tool"

    def simulate(self, intent: ExecutionIntent, *, execution_mode: str) -> ExecutionResult:
        raise NotImplementedError


class SoftwareToolAdapter(ExecutionAdapter):
    adapter_type = "software_tool"

    def simulate(self, intent: ExecutionIntent, *, execution_mode: str) -> ExecutionResult:
        return _build_execution_result(
            intent,
            adapter_type=self.adapter_type,
            execution_mode=execution_mode,
            success=True,
            output_text=(
                f"Would call software tool '{intent.target_name}' "
                f"for action '{intent.action_type}' with parameters {json.dumps(intent.parameters, ensure_ascii=False)}."
            ),
            output_data={"simulated_call": intent.parameters},
        )


class LocalScriptAdapter(ExecutionAdapter):
    adapter_type = "local_script"

    def simulate(self, intent: ExecutionIntent, *, execution_mode: str) -> ExecutionResult:
        return _build_execution_result(
            intent,
            adapter_type=self.adapter_type,
            execution_mode=execution_mode,
            success=True,
            output_text=(
                f"Would run local script target '{intent.target_name}' "
                f"for action '{intent.action_type}'."
            ),
            output_data={"script_parameters": intent.parameters},
        )


class SimulatedDeviceAdapter(ExecutionAdapter):
    adapter_type = "simulated_device"

    def simulate(self, intent: ExecutionIntent, *, execution_mode: str) -> ExecutionResult:
        return _build_execution_result(
            intent,
            adapter_type=self.adapter_type,
            execution_mode=execution_mode,
            success=True,
            output_text=(
                f"Would send simulated command '{intent.action_type}' "
                f"to device '{intent.target_name}'."
            ),
            output_data={"device_command": intent.parameters},
        )


class RoboticCarrierAdapter(ExecutionAdapter):
    adapter_type = "robotic_carrier"

    def simulate(self, intent: ExecutionIntent, *, execution_mode: str) -> ExecutionResult:
        return _build_execution_result(
            intent,
            adapter_type=self.adapter_type,
            execution_mode=execution_mode,
            success=True,
            output_text=(
                f"Placeholder only. Would route '{intent.action_type}' "
                f"to robotic carrier '{intent.target_name}', but no real action is taken."
            ),
            output_data={"placeholder": True, "requested_parameters": intent.parameters},
        )


def propose_execution_intent(
    config: AppConfig,
    *,
    source_session_id: str | None,
    action_type: str,
    target_type: str,
    target_name: str,
    parameters: dict[str, Any] | None,
    rationale: str,
    requires_confirmation: bool = True,
    safety_level: str = "medium",
    snapshot_scope: str = "all",
) -> ExecutionOperationResult:
    normalized_parameters = parameters or {}
    intent_key = build_execution_intent_key(
        source_session_id=source_session_id,
        action_type=action_type,
        target_type=target_type,
        target_name=target_name,
        parameters=normalized_parameters,
        rationale=rationale,
        snapshot_scope=snapshot_scope,
    )

    with get_connection(config.database_path) as connection:
        existing_intent = find_execution_intent_by_key(connection, intent_key)
        if existing_intent is not None:
            return ExecutionOperationResult(
                status="existing",
                message=f"Execution intent already exists as {existing_intent.intent_id}.",
                intent=existing_intent,
                intent_artifact_path=_intent_artifact_path(config, existing_intent.intent_id),
            )

        source_audit_id = None
        persona_core_version_id = None
        effective_scope = snapshot_scope
        if source_session_id:
            session = get_session_record(connection, source_session_id)
            if session is None:
                return ExecutionOperationResult(
                    status="missing",
                    message=f"No session found for {source_session_id}.",
                )
            effective_scope = session.snapshot_scope
            persona_core_version_id = session.persona_core_version_id
            audit = get_audit_record(connection, source_session_id)
            if audit is None:
                ensured = ensure_audit_record(config, source_session_id, connection=connection)
                audit = ensured.audit_record
            source_audit_id = audit.audit_id if audit is not None else None
        else:
            current_persona = get_current_persona_core_version(connection, snapshot_scope=snapshot_scope)
            if current_persona is not None:
                persona_core_version_id = current_persona[0]

        intent = ExecutionIntent(
            intent_id=new_id("exi"),
            created_at=utc_now(),
            source_session_id=source_session_id,
            source_audit_id=source_audit_id,
            action_type=action_type.strip(),
            target_type=target_type,
            target_name=target_name.strip(),
            parameters=normalized_parameters,
            rationale=rationale.strip(),
            requires_confirmation=requires_confirmation,
            safety_level=safety_level,
            status="proposed",
            review_status="pending",
            review_note="",
            review_updated_at=None,
            snapshot_scope=effective_scope,
            persona_core_version_id=persona_core_version_id,
        )
        artifact_path = write_execution_intent_artifact(config, intent)
        insert_execution_intent(
            connection,
            intent,
            intent_key=intent_key,
            artifact_path=artifact_path,
        )

    return ExecutionOperationResult(
        status="created",
        message=f"Created execution intent {intent.intent_id}.",
        intent=intent,
        intent_artifact_path=artifact_path,
    )


def simulate_execution_intent(
    config: AppConfig,
    intent_id: str,
    *,
    execution_mode: str = "simulation",
) -> ExecutionOperationResult:
    with get_connection(config.database_path) as connection:
        intent = get_execution_intent(connection, intent_id)
        if intent is None:
            return ExecutionOperationResult(
                status="missing",
                message=f"No execution intent found for {intent_id}.",
            )

        if intent.status == "rejected":
            result = _build_execution_result(
                intent,
                adapter_type=intent.target_type,
                execution_mode=execution_mode,
                success=False,
                output_text="",
                output_data={},
                error_text="Rejected intents cannot be executed.",
            )
            result_artifact_path = write_execution_result_artifact(config, result)
            insert_execution_result(connection, result, artifact_path=result_artifact_path)
            return ExecutionOperationResult(
                status="rejected",
                message=f"Intent {intent.intent_id} is rejected and cannot be executed.",
                intent=intent,
                result=result,
                intent_artifact_path=_intent_artifact_path(config, intent.intent_id),
                result_artifact_path=result_artifact_path,
            )

        adapter = select_execution_adapter(intent.target_type)
        result = adapter.simulate(intent, execution_mode=execution_mode)
        result_artifact_path = write_execution_result_artifact(config, result)
        insert_execution_result(connection, result, artifact_path=result_artifact_path)

        if result.success:
            intent.status = "simulated"
        else:
            intent.status = "failed"
        intent_artifact_path = write_execution_intent_artifact(config, intent)
        update_execution_intent(connection, intent, artifact_path=intent_artifact_path)

    return ExecutionOperationResult(
        status="simulated" if result.success else "failed",
        message=f"Execution intent {intent.intent_id} processed through the simulator.",
        intent=intent,
        result=result,
        intent_artifact_path=intent_artifact_path,
        result_artifact_path=result_artifact_path,
    )


def approve_and_run_execution_intent(
    config: AppConfig, intent_id: str
) -> ExecutionOperationResult:
    with get_connection(config.database_path) as connection:
        intent = get_execution_intent(connection, intent_id)
        if intent is None:
            return ExecutionOperationResult(
                status="missing",
                message=f"No execution intent found for {intent_id}.",
            )
        if intent.status == "rejected":
            return ExecutionOperationResult(
                status="rejected",
                message=f"Intent {intent.intent_id} is rejected and cannot be approved.",
                intent=intent,
                intent_artifact_path=_intent_artifact_path(config, intent.intent_id),
            )
        intent.status = "approved"
        intent_artifact_path = write_execution_intent_artifact(config, intent)
        update_execution_intent(connection, intent, artifact_path=intent_artifact_path)

    return simulate_execution_intent(
        config,
        intent_id,
        execution_mode="approved_simulation",
    )


def reject_execution_intent(config: AppConfig, intent_id: str) -> ExecutionOperationResult:
    with get_connection(config.database_path) as connection:
        intent = get_execution_intent(connection, intent_id)
        if intent is None:
            return ExecutionOperationResult(
                status="missing",
                message=f"No execution intent found for {intent_id}.",
            )

        intent.status = "rejected"
        artifact_path = write_execution_intent_artifact(config, intent)
        update_execution_intent(connection, intent, artifact_path=artifact_path)

    return ExecutionOperationResult(
        status="rejected",
        message=f"Rejected execution intent {intent.intent_id}.",
        intent=intent,
        intent_artifact_path=artifact_path,
    )


def review_execution_intent(
    config: AppConfig,
    intent_id: str,
    *,
    review_status: str,
    review_note: str,
) -> ExecutionOperationResult:
    with get_connection(config.database_path) as connection:
        intent = get_execution_intent(connection, intent_id)
        if intent is None:
            return ExecutionOperationResult(
                status="missing",
                message=f"No execution intent found for {intent_id}.",
            )
        intent.review_status = review_status
        intent.review_note = review_note.strip()
        intent.review_updated_at = utc_now()
        artifact_path = write_execution_intent_artifact(config, intent)
        update_execution_intent(connection, intent, artifact_path=artifact_path)

    return ExecutionOperationResult(
        status="reviewed",
        message=f"Updated review for execution intent {intent.intent_id}.",
        intent=intent,
        intent_artifact_path=artifact_path,
    )


def list_execution_items(config: AppConfig, *, limit: int = 20) -> tuple[list[ExecutionIntent], list[ExecutionResult]]:
    with get_connection(config.database_path) as connection:
        intents = list_execution_intents(connection, limit=limit)
        results = list_execution_results(connection, limit=limit)
    return intents, results


def get_execution_detail(config: AppConfig, intent_id: str) -> ExecutionDetail:
    with get_connection(config.database_path) as connection:
        intent = get_execution_intent(connection, intent_id)
        results = list_execution_results(connection, limit=50, intent_id=intent_id)
    return ExecutionDetail(intent=intent, results=results)


def format_execution_list(intents: list[ExecutionIntent]) -> str:
    if not intents:
        return "No execution intents found."
    header = "intent_id                             status      review       safety  target_type        target_name"
    separator = "-" * len(header)
    lines = [header, separator]
    for intent in intents:
        lines.append(
            f"{intent.intent_id:<36} {intent.status:<11} {intent.review_status:<12} {intent.safety_level:<7} {intent.target_type:<18} {intent.target_name}"
        )
    return "\n".join(lines)


def format_execution_detail(detail: ExecutionDetail) -> str:
    if detail.intent is None:
        return "Execution intent not found."
    intent = detail.intent
    lines = [
        "Execution Intent",
        f"intent_id: {intent.intent_id}",
        f"status: {intent.status}",
        f"action_type: {intent.action_type}",
        f"target_type: {intent.target_type}",
        f"target_name: {intent.target_name}",
        f"requires_confirmation: {intent.requires_confirmation}",
        f"safety_level: {intent.safety_level}",
        f"review_status: {intent.review_status}",
        f"review_note: {intent.review_note or 'None'}",
        f"source_session_id: {intent.source_session_id or 'None'}",
        f"source_audit_id: {intent.source_audit_id or 'None'}",
        f"snapshot_scope: {intent.snapshot_scope}",
        f"persona_core_version_id: {intent.persona_core_version_id or 'None'}",
        f"rationale: {intent.rationale or 'None'}",
        f"parameters: {json.dumps(intent.parameters, ensure_ascii=False)}",
    ]
    if detail.results:
        latest = detail.results[0]
        lines.extend(
            [
                f"latest_result_id: {latest.result_id}",
                f"latest_result_success: {latest.success}",
                f"latest_result_mode: {latest.execution_mode}",
                f"latest_result_output: {latest.output_text or latest.error_text or 'None'}",
            ]
        )
    return "\n".join(lines)


def parse_execution_parameters(parameters_text: str) -> dict[str, Any]:
    cleaned = parameters_text.strip()
    if not cleaned:
        return {}
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("Execution parameters must be a JSON object.")
    return payload


def build_execution_intent_key(
    *,
    source_session_id: str | None,
    action_type: str,
    target_type: str,
    target_name: str,
    parameters: dict[str, Any],
    rationale: str,
    snapshot_scope: str,
) -> str:
    return sha256_text(
        json.dumps(
            {
                "source_session_id": source_session_id,
                "action_type": action_type.strip(),
                "target_type": target_type,
                "target_name": target_name.strip(),
                "parameters": parameters,
                "rationale": rationale.strip(),
                "snapshot_scope": snapshot_scope,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def select_execution_adapter(target_type: str) -> ExecutionAdapter:
    adapters = {
        "software_tool": SoftwareToolAdapter(),
        "local_script": LocalScriptAdapter(),
        "simulated_device": SimulatedDeviceAdapter(),
        "robotic_carrier": RoboticCarrierAdapter(),
    }
    return adapters[target_type]


def write_execution_intent_artifact(config: AppConfig, intent: ExecutionIntent) -> Path:
    artifact_path = _intent_artifact_path(config, intent.intent_id)
    write_json(artifact_path, intent.model_dump(mode="json"))
    return artifact_path


def write_execution_result_artifact(config: AppConfig, result: ExecutionResult) -> Path:
    artifact_path = config.execution_dir / f"result_{result.result_id}.json"
    write_json(artifact_path, result.model_dump(mode="json"))
    return artifact_path


def _intent_artifact_path(config: AppConfig, intent_id: str) -> Path:
    return config.execution_dir / f"intent_{intent_id}.json"


def _build_execution_result(
    intent: ExecutionIntent,
    *,
    adapter_type: str,
    execution_mode: str,
    success: bool,
    output_text: str,
    output_data: dict[str, Any],
    error_text: str | None = None,
) -> ExecutionResult:
    return ExecutionResult(
        result_id=new_id("exr"),
        intent_id=intent.intent_id,
        created_at=utc_now(),
        adapter_type=adapter_type,
        execution_mode=execution_mode,
        success=success,
        output_text=output_text,
        output_data=output_data,
        error_text=error_text,
    )
