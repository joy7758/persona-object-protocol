from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib import error, request

from pop_cockpit.prompts import (
    ASK_ANALYSIS_SYSTEM_PROMPT,
    DAILY_EXTRACTION_SYSTEM_PROMPT,
    PERSONA_REBUILD_SYSTEM_PROMPT,
    build_ask_analysis_prompt,
    build_persona_rebuild_prompt,
)
from pop_cockpit.schemas import (
    DailyExtractionRequest,
    DailyPersonaSnapshot,
    DailyPersonaSnapshotDraft,
    PersonaCore,
    ProjectSettings,
)
from pop_cockpit.utils import utc_now

JSON_ONLY_SUFFIX = """

Return valid JSON only.
Do not wrap the JSON in markdown fences.
"""


class ProviderError(RuntimeError):
    """Raised when an API provider cannot be used successfully."""


@dataclass(slots=True)
class ProviderConnectionResult:
    success: bool
    checked_at: datetime
    message: str


class OpenAICompatibleClient:
    def __init__(self, *, base_url: str, api_key: str, timeout_seconds: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def chat_completion_text(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        response_payload = self._post_json("/chat/completions", payload)
        try:
            choice = response_payload["choices"][0]
            message = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("API 返回内容不符合预期。") from exc

        if isinstance(message, list):
            parts: list[str] = []
            for item in message:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "\n".join(part for part in parts if part).strip()
        return str(message).strip()

    def chat_completion_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        content = self.chat_completion_text(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
        return _parse_json_from_text(content)

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.base_url or not self.api_key:
            raise ProviderError("AI 接口地址或密钥还没有配置。")

        target_url = f"{self.base_url}{path}"
        http_request = request.Request(
            target_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                payload_text = response.read().decode("utf-8")
        except error.HTTPError as exc:
            payload_text = exc.read().decode("utf-8", errors="ignore")
            message = _extract_provider_error_message(payload_text) or f"HTTP {exc.code}"
            raise ProviderError(f"AI 接口请求失败：{message}") from exc
        except error.URLError as exc:
            raise ProviderError(f"无法连接到 AI 接口：{exc.reason}") from exc

        try:
            return json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ProviderError("AI 接口返回了无法解析的内容。") from exc


class ApiDailyExtractionProvider:
    name = "api"

    def __init__(self, *, client: OpenAICompatibleClient, model: str) -> None:
        self.client = client
        self.model = model
        self.name = f"api:{model}"

    def extract_daily(self, request_payload: DailyExtractionRequest) -> DailyPersonaSnapshotDraft:
        response_payload = self.client.chat_completion_json(
            model=self.model,
            system_prompt=DAILY_EXTRACTION_SYSTEM_PROMPT + JSON_ONLY_SUFFIX,
            user_prompt=request_payload.prompt
            + "\n\nReturn these keys: goal_priority, current_focus, decision_style, risk_profile, recurring_topics, stable_biases, emotional_signals, new_traits, important_decisions, confidence_notes.",
        )
        return DailyPersonaSnapshotDraft(
            date_range=request_payload.date_range,
            source_record_ids=[record.id for record in request_payload.records],
            goal_priority=_coerce_list(response_payload.get("goal_priority")),
            current_focus=_coerce_list(response_payload.get("current_focus")),
            decision_style=_coerce_string(response_payload.get("decision_style")),
            risk_profile=_coerce_string(response_payload.get("risk_profile")),
            recurring_topics=_coerce_list(response_payload.get("recurring_topics")),
            stable_biases=_coerce_list(response_payload.get("stable_biases")),
            emotional_signals=_coerce_list(response_payload.get("emotional_signals")),
            new_traits=_coerce_list(response_payload.get("new_traits")),
            important_decisions=_coerce_list(response_payload.get("important_decisions")),
            confidence_notes=_coerce_list(response_payload.get("confidence_notes"))
            + [f"API provider used: {self.model}"],
            provider_name=self.name,
            metadata={"record_count": len(request_payload.records), "model": self.model},
        )


class OpenAICompatibleAskProvider:
    name = "api"

    def __init__(self, *, client: OpenAICompatibleClient, model: str) -> None:
        self.client = client
        self.model = model
        self.name = f"api:{model}"

    def answer(self, prompt_context: str) -> str:
        return self.client.chat_completion_text(
            model=self.model,
            system_prompt=ASK_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=build_ask_analysis_prompt(prompt_context),
            temperature=0.3,
        )


def build_persona_core_with_api(
    *,
    client: OpenAICompatibleClient,
    model: str,
    snapshots: list[DailyPersonaSnapshot],
    snapshot_scope: str,
) -> PersonaCore:
    response_payload = client.chat_completion_json(
        model=model,
        system_prompt=PERSONA_REBUILD_SYSTEM_PROMPT + JSON_ONLY_SUFFIX,
        user_prompt=build_persona_rebuild_prompt(snapshots, snapshot_scope)
        + "\n\nReturn these keys: identity, long_term_goals, current_focus, decision_style, risk_profile, stable_biases, recurring_topics, expression_style, taboos_and_boundaries, recent_shifts, evidence_summary, confidence_notes.",
    )
    return PersonaCore(
        identity=_coerce_string(response_payload.get("identity")),
        long_term_goals=_coerce_list(response_payload.get("long_term_goals")),
        current_focus=_coerce_list(response_payload.get("current_focus")),
        decision_style=_coerce_string(response_payload.get("decision_style")),
        risk_profile=_coerce_string(response_payload.get("risk_profile")),
        stable_biases=_coerce_list(response_payload.get("stable_biases")),
        recurring_topics=_coerce_list(response_payload.get("recurring_topics")),
        expression_style=_coerce_list(response_payload.get("expression_style")),
        taboos_and_boundaries=_coerce_list(response_payload.get("taboos_and_boundaries")),
        recent_shifts=_coerce_list(response_payload.get("recent_shifts")),
        evidence_summary=_coerce_list(response_payload.get("evidence_summary")),
        confidence_notes=_coerce_list(response_payload.get("confidence_notes"))
        + [f"API provider used: {model}"],
        source_snapshot_ids=[snapshot.id for snapshot in snapshots],
        snapshot_scope=snapshot_scope,
        last_updated=utc_now(),
    )


def build_provider_client(settings: ProjectSettings) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        base_url=settings.api_base_url.strip(),
        api_key=settings.api_key.strip(),
    )


def resolve_task_model(settings: ProjectSettings, task: str) -> str:
    specific_map = {
        "extract": settings.extract_model,
        "persona": settings.persona_model,
        "ask": settings.ask_model,
    }
    specific_value = specific_map.get(task, "")
    if specific_value and specific_value.strip():
        return specific_value.strip()
    return settings.default_model.strip()


def mask_api_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def test_provider_connection(settings: ProjectSettings) -> ProviderConnectionResult:
    model = resolve_task_model(settings, "ask") or settings.default_model.strip()
    if not settings.api_base_url.strip():
        raise ProviderError("还没有填写 API 地址。")
    if not settings.api_key.strip():
        raise ProviderError("还没有填写 API 密钥。")
    if not model:
        raise ProviderError("还没有填写默认模型或提问分析模型。")

    client = build_provider_client(settings)
    reply = client.chat_completion_text(
        model=model,
        system_prompt="Reply with a short confirmation only.",
        user_prompt="Reply with: POP connection ok.",
        temperature=0,
        max_tokens=12,
    )
    return ProviderConnectionResult(
        success=True,
        checked_at=utc_now(),
        message=f"连接成功，模型返回：{reply or 'POP connection ok.'}",
    )


def provider_status_text(settings: ProjectSettings) -> str:
    status_map = {
        "not_tested": "未测试",
        "success": "连接正常",
        "failed": "连接失败",
    }
    return status_map.get(settings.last_provider_test_status, settings.last_provider_test_status)


def _parse_json_from_text(value: str) -> dict[str, Any]:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ProviderError("AI 接口没有返回有效的 JSON。")
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ProviderError("AI 接口返回的 JSON 无法解析。") from exc
    if not isinstance(payload, dict):
        raise ProviderError("AI 接口返回的 JSON 不是对象结构。")
    return payload


def _extract_provider_error_message(payload_text: str) -> str | None:
    if not payload_text.strip():
        return None
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return payload_text.strip()
    if isinstance(payload, dict):
        error_payload = payload.get("error")
        if isinstance(error_payload, dict):
            message = error_payload.get("message")
            if message:
                return str(message)
        message = payload.get("message")
        if message:
            return str(message)
    return payload_text.strip()


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    return [str(value).strip()] if str(value).strip() else []


def _coerce_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
