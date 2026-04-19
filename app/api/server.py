from __future__ import annotations

import argparse
import json
import threading
import time
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app.models import (
    CODEX_AUTOMATION_MODE_OPTIONS,
    CODEX_AUTOMATION_PRESETS,
    DEEP_INTEGRATION_MODE_OPTIONS,
    DEEP_INTEGRATION_READINESS_OPTIONS,
    JUDGMENT_ENGINE_MODE_OPTIONS,
    LIVE_OPS_PROFILE_OPTIONS,
    LIVE_OPS_REENTRY_OPTIONS,
    LIVE_OPS_REPORT_CADENCE_OPTIONS,
    RuntimeState,
    SessionConfig,
    VISUAL_CAPTURE_SCOPE_OPTIONS,
    VISUAL_RETENTION_OPTIONS,
    VISUAL_TARGET_MODE_OPTIONS,
)
from app.automation.windows_ui import WindowResolution, WindowsDesktopBridge
from app.services.workflow import AutomationEngine
from app.state import SessionStore


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _excerpt(text: str, *, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit].rstrip()}..."


def _tone_for_flag(*, ready: bool, warning: bool = False) -> str:
    if warning:
        return "warn"
    return "good" if ready else "muted"


def _option_payload(option_id: str, title: str, summary: str) -> dict[str, str]:
    return {
        "id": option_id,
        "title": title,
        "summary": summary,
    }


def _activity_tone(message: str) -> str:
    lowered = message.lower()
    if any(token in lowered for token in ("[오류]", "실패", "error", "retry", "ask_user")):
        return "warn"
    if any(token in lowered for token in ("저장", "생성", "전송", "완료", "복원", "시작")):
        return "good"
    return "muted"


class LocalBridgeService:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.store = SessionStore(workspace)
        self.bridge = WindowsDesktopBridge()
        self.engine = AutomationEngine(self.bridge, self.store.capture_dir)
        self._lock = threading.RLock()
        self._auto_thread: threading.Thread | None = None
        self._auto_stop_event = threading.Event()

    def is_auto_running(self) -> bool:
        return self._auto_thread is not None and self._auto_thread.is_alive()

    def build_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return _build_snapshot_payload(self)

    def build_control_deck(self) -> dict[str, Any]:
        with self._lock:
            return _build_control_deck_payload(self)

    def build_workspace_bundle(self) -> dict[str, Any]:
        with self._lock:
            return _build_workspace_bundle_payload(self)

    def shutdown(self) -> None:
        with self._lock:
            self._stop_auto_loop()

    def perform_action(self, action_id: str) -> dict[str, Any]:
        if action_id == "open_settings":
            return {
                "ok": True,
                "actionId": action_id,
                "message": "이 액션은 web shell 내부 drawer에서 처리됩니다.",
                "payload": {"localOnly": True},
                "snapshot": self.build_snapshot(),
            }

        with self._lock:
            if action_id == "start_auto":
                message = self._start_auto_loop()
                return {
                    "ok": True,
                    "actionId": action_id,
                    "message": message,
                    "payload": {"autoRunning": self.is_auto_running()},
                    "snapshot": _build_snapshot_payload(self),
                }

            persisted = self.store.load()
            session = persisted.session
            runtime = persisted.runtime

            if action_id == "pause_auto":
                if self.is_auto_running():
                    self._stop_auto_loop()
                    reason = "web shell에서 보류를 요청해서 자동 감시를 멈췄습니다."
                else:
                    reason = "web shell에서 보류를 요청했습니다."
                runtime.set_operator_pause(reason)
                self.store.save(persisted)
                self.store.append_log(reason)
                return self._success(action_id, reason)

            if action_id == "resume_ready":
                runtime.clear_operator_pause()
                self.store.save(persisted)
                message = "보류 상태를 해제했습니다."
                self.store.append_log(message)
                return self._success(action_id, message)

            if action_id == "continue":
                runtime.clear_operator_pause()
                report = self.engine.send_next_step_now(session, runtime)
                self.store.save(persisted)
                self._append_report_logs(report)
                return self._success(
                    action_id,
                    self._format_report(report),
                    payload={"report": self._serialize_report(report)},
                )

            if action_id == "refresh_windows":
                resolution = self.bridge.resolve_target(session.window)
                self._sync_runtime_from_resolution(runtime, resolution)
                self.store.save(persisted)
                message = f"창 상태를 다시 확인했습니다. {resolution.summary()}"
                self.store.append_log(message)
                return self._success(action_id, message, payload={"resolution": resolution.summary()})

            if action_id == "focus_codex":
                resolution = self._resolve_target(session, runtime)
                self.bridge.focus_window(resolution.selected.handle)
                self._remember_resolution(session, resolution)
                self.store.save(persisted)
                message = f"Codex 창에 포커스를 맞췄습니다. {resolution.summary()}"
                self.store.append_log(message)
                return self._success(action_id, message, payload={"resolution": resolution.summary()})

            if action_id == "capture_now":
                resolution = self._resolve_target(session, runtime)
                capture_path = self.store.capture_dir / f"web-shell-{int(time.time())}.bmp"
                self.bridge.capture_window(resolution.selected.handle, capture_path)
                runtime.last_capture_path = str(capture_path)
                self._remember_resolution(session, resolution)
                self.store.save(persisted)
                message = f"Codex 창을 캡처했습니다. {capture_path.name}"
                self.store.append_log(message)
                return self._success(action_id, message, payload={"capturePath": str(capture_path)})

            if action_id == "voice_brief":
                briefing = self.engine.build_voice_briefing(session, runtime)
                self.store.save(persisted)
                message = "브리핑을 생성했습니다."
                self.store.append_log(message)
                return self._success(action_id, message, payload={"briefing": briefing})

            if action_id == "show_summary":
                summary = self._build_status_summary(session, runtime)
                return self._success(action_id, "현재 상태 요약을 만들었습니다.", payload={"summary": summary})

            if action_id == "rejudge":
                result = self.engine.run_judgment(session, runtime, recent_log_lines=self._recent_log_lines())
                if result.decision == "retry" and (result.next_prompt_to_codex or "").strip():
                    runtime.update_prompt_draft(result.next_prompt_to_codex.strip())
                if result.decision in {"pause", "ask_user"}:
                    runtime.set_operator_pause(result.message_to_user or result.reason)
                elif result.decision == "continue":
                    runtime.clear_operator_pause()
                self.store.save(persisted)
                message = f"재판단 완료: {result.decision} | conf {result.confidence:.2f} | risk {result.risk_level}"
                self.store.append_log(message)
                return self._success(
                    action_id,
                    message,
                    payload={
                        "decision": result.decision,
                        "reason": result.reason,
                        "confidence": result.confidence,
                    },
                )

            if action_id == "retry_now":
                result = runtime.last_judgment
                if not result.has_result or result.decision != "retry" or not (result.next_prompt_to_codex or "").strip():
                    raise ValueError("현재 retry 가능한 판단 결과가 없어 보정 프롬프트를 바로 보낼 수 없습니다.")
                runtime.update_prompt_draft(result.next_prompt_to_codex.strip())
                report = self.engine.send_next_step_now(session, runtime)
                self.store.save(persisted)
                self._append_report_logs(report)
                return self._success(
                    action_id,
                    self._format_report(report),
                    payload={"report": self._serialize_report(report)},
                )

            raise ValueError(f"지원하지 않는 action 입니다: {action_id}")

    def update_control_deck(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            persisted = self.store.load()
            session = persisted.session
            runtime = persisted.runtime

            if kind == "project":
                project = payload.get("project", {})
                previous_steps = session.project.steps_text
                session.project.project_summary = str(project.get("projectSummary", session.project.project_summary)).strip()
                session.project.target_outcome = str(project.get("targetOutcome", session.project.target_outcome)).strip()
                session.project.steps_text = str(project.get("stepsText", session.project.steps_text)).strip()
                runtime.clear_prompt_preview()
                if session.project.steps_text != previous_steps:
                    runtime.next_step_index = min(runtime.next_step_index, len(session.project.steps()))
                    runtime.stable_cycles = 0
                if self.is_auto_running():
                    self._stop_auto_loop()
                message = "프로젝트 요약과 단계 계획을 저장했습니다."
            elif kind == "operations":
                operations = payload.get("operations", {})
                strategy = operations.get("codexStrategy", {})
                automation = operations.get("automation", {})
                live_ops = operations.get("liveOps", {})

                preset_ids = {option.preset_id for option in CODEX_AUTOMATION_PRESETS}
                mode_ids = {option.mode_id for option in CODEX_AUTOMATION_MODE_OPTIONS}
                profile_ids = {option.profile_id for option in LIVE_OPS_PROFILE_OPTIONS}
                cadence_ids = {option.cadence_id for option in LIVE_OPS_REPORT_CADENCE_OPTIONS}
                reentry_ids = {option.reentry_id for option in LIVE_OPS_REENTRY_OPTIONS}

                selected_preset = str(strategy.get("selectedPresetId", session.codex_strategy.selected_preset_id)).strip()
                if selected_preset in preset_ids:
                    session.codex_strategy.selected_preset_id = selected_preset

                selected_mode = str(strategy.get("selectedModeId", session.codex_strategy.selected_mode_id)).strip()
                if selected_mode in mode_ids:
                    session.codex_strategy.selected_mode_id = selected_mode

                session.codex_strategy.custom_instruction = str(
                    strategy.get("customInstruction", session.codex_strategy.custom_instruction)
                ).strip()

                try:
                    poll_interval_sec = int(automation.get("pollIntervalSec", session.automation.poll_interval_sec) or 0)
                except (TypeError, ValueError):
                    poll_interval_sec = session.automation.poll_interval_sec
                session.automation.poll_interval_sec = max(1, min(poll_interval_sec, 3600))
                session.automation.dry_run = bool(automation.get("dryRun", session.automation.dry_run))

                selected_profile = str(live_ops.get("selectedProfileId", session.live_ops.selected_profile_id)).strip()
                if selected_profile in profile_ids:
                    session.live_ops.selected_profile_id = selected_profile

                selected_cadence = str(live_ops.get("reportCadenceId", session.live_ops.report_cadence_id)).strip()
                if selected_cadence in cadence_ids:
                    session.live_ops.report_cadence_id = selected_cadence

                selected_reentry = str(live_ops.get("reentryModeId", session.live_ops.reentry_mode_id)).strip()
                if selected_reentry in reentry_ids:
                    session.live_ops.reentry_mode_id = selected_reentry

                session.live_ops.operator_note = str(live_ops.get("operatorNote", session.live_ops.operator_note)).strip()
                runtime.clear_prompt_preview()
                message = "운영 설정과 Codex 전략을 저장했습니다."
            elif kind == "prompt":
                preview = self.engine.build_prompt_preview(session, runtime)
                action = str(payload.get("action", "save")).strip() or "save"
                if not preview.has_step:
                    raise ValueError("현재 편집 가능한 단계 프롬프트가 없습니다.")
                if action == "reset":
                    runtime.update_prompt_draft(preview.generated_prompt)
                    message = "현재 단계 프롬프트를 원문으로 되돌렸습니다."
                else:
                    draft_prompt = str(payload.get("draftPrompt", preview.draft_prompt))
                    runtime.update_prompt_draft(draft_prompt.strip())
                    message = "현재 단계 프롬프트 draft를 저장했습니다."
            elif kind == "intelligence":
                intelligence = payload.get("intelligence", {})
                judgment = intelligence.get("judgment", {})
                visual = intelligence.get("visual", {})
                voice = intelligence.get("voice", {})
                deep = intelligence.get("deepIntegration", {})

                judgment_mode_ids = {option.mode_id for option in JUDGMENT_ENGINE_MODE_OPTIONS}
                visual_target_ids = {option.mode_id for option in VISUAL_TARGET_MODE_OPTIONS}
                visual_scope_ids = {option.scope_id for option in VISUAL_CAPTURE_SCOPE_OPTIONS}
                visual_retention_ids = {option.retention_id for option in VISUAL_RETENTION_OPTIONS}
                deep_mode_ids = {option.mode_id for option in DEEP_INTEGRATION_MODE_OPTIONS}
                deep_readiness_ids = {option.readiness_id for option in DEEP_INTEGRATION_READINESS_OPTIONS}

                judgment_mode = str(judgment.get("engineModeId", session.judgment.engine_mode_id)).strip()
                if judgment_mode in judgment_mode_ids:
                    session.judgment.engine_mode_id = judgment_mode
                session.judgment.model_name = str(judgment.get("modelName", session.judgment.model_name)).strip()
                try:
                    confidence_threshold = float(
                        judgment.get("confidenceThreshold", session.judgment.confidence_threshold) or 0.0
                    )
                except (TypeError, ValueError):
                    confidence_threshold = session.judgment.confidence_threshold
                session.judgment.confidence_threshold = max(0.0, min(confidence_threshold, 1.0))
                try:
                    max_history_items = int(judgment.get("maxHistoryItems", session.judgment.max_history_items) or 0)
                except (TypeError, ValueError):
                    max_history_items = session.judgment.max_history_items
                session.judgment.max_history_items = max(1, min(max_history_items, 20))

                visual_target = str(visual.get("targetModeId", session.visual.target_mode_id)).strip()
                if visual_target in visual_target_ids:
                    session.visual.target_mode_id = visual_target
                visual_scope = str(visual.get("captureScopeId", session.visual.capture_scope_id)).strip()
                if visual_scope in visual_scope_ids:
                    session.visual.capture_scope_id = visual_scope
                visual_retention = str(visual.get("retentionHintId", session.visual.retention_hint_id)).strip()
                if visual_retention in visual_retention_ids:
                    session.visual.retention_hint_id = visual_retention
                session.visual.sensitive_content_risk = str(
                    visual.get("sensitiveContentRisk", session.visual.sensitive_content_risk)
                ).strip()
                session.visual.expected_page = str(visual.get("expectedPage", session.visual.expected_page)).strip()
                session.visual.expected_signals_text = str(
                    visual.get("expectedSignalsText", session.visual.expected_signals_text)
                ).strip()
                session.visual.disallowed_signals_text = str(
                    visual.get("disallowedSignalsText", session.visual.disallowed_signals_text)
                ).strip()
                session.visual.observation_focus_text = str(
                    visual.get("observationFocusText", session.visual.observation_focus_text)
                ).strip()
                session.visual.observed_notes_text = str(
                    visual.get("observedNotesText", session.visual.observed_notes_text)
                ).strip()

                session.voice.language_code = str(voice.get("languageCode", session.voice.language_code)).strip()
                session.voice.auto_brief_enabled = bool(voice.get("autoBriefEnabled", session.voice.auto_brief_enabled))
                session.voice.confirmation_enabled = bool(
                    voice.get("confirmationEnabled", session.voice.confirmation_enabled)
                )
                session.voice.spoken_feedback_enabled = bool(
                    voice.get("spokenFeedbackEnabled", session.voice.spoken_feedback_enabled)
                )
                session.voice.ambient_ready_enabled = bool(
                    voice.get("ambientReadyEnabled", session.voice.ambient_ready_enabled)
                )
                session.voice.microphone_name = str(voice.get("microphoneName", session.voice.microphone_name)).strip()
                session.voice.speaker_name = str(voice.get("speakerName", session.voice.speaker_name)).strip()

                deep_mode = str(deep.get("selectedModeId", session.deep_integration.selected_mode_id)).strip()
                if deep_mode in deep_mode_ids:
                    session.deep_integration.selected_mode_id = deep_mode
                app_server_readiness = str(
                    deep.get("appServerReadinessId", session.deep_integration.app_server_readiness_id)
                ).strip()
                if app_server_readiness in deep_readiness_ids:
                    session.deep_integration.app_server_readiness_id = app_server_readiness
                cloud_trigger_readiness = str(
                    deep.get("cloudTriggerReadinessId", session.deep_integration.cloud_trigger_readiness_id)
                ).strip()
                if cloud_trigger_readiness in deep_readiness_ids:
                    session.deep_integration.cloud_trigger_readiness_id = cloud_trigger_readiness
                session.deep_integration.desktop_fallback_allowed = bool(
                    deep.get("desktopFallbackAllowed", session.deep_integration.desktop_fallback_allowed)
                )
                session.deep_integration.app_server_notes = str(
                    deep.get("appServerNotes", session.deep_integration.app_server_notes)
                ).strip()
                session.deep_integration.cloud_trigger_notes = str(
                    deep.get("cloudTriggerNotes", session.deep_integration.cloud_trigger_notes)
                ).strip()
                session.deep_integration.handoff_notes = str(
                    deep.get("handoffNotes", session.deep_integration.handoff_notes)
                ).strip()
                message = "Intelligence Studio 설정을 저장했습니다."
            elif kind == "recent_project":
                try:
                    recent_index = int(payload.get("recentIndex", -1))
                except (TypeError, ValueError):
                    recent_index = -1
                if recent_index < 0 or recent_index >= len(persisted.recent_projects):
                    raise ValueError("복원할 최근 프로젝트를 찾지 못했습니다.")
                entry = persisted.recent_projects[recent_index]
                persisted.session = SessionConfig.from_dict(entry.session.to_dict())
                persisted.runtime = RuntimeState.from_persisted_dict(entry.runtime.to_persisted_dict())
                persisted.runtime.auto_running = False
                session = persisted.session
                runtime = persisted.runtime
                if self.is_auto_running():
                    self._stop_auto_loop()
                message = f"최근 프로젝트를 현재 세션으로 복원했습니다. {entry.project_summary or entry.target_outcome or '이름 없는 프로젝트'}"
            else:
                raise ValueError(f"지원하지 않는 control deck 요청입니다: {kind}")

            self.store.save(persisted)
            self.store.append_log(message)
            return {
                "ok": True,
                "kind": kind,
                "message": message,
                "snapshot": _build_snapshot_payload(self),
                "controlDeck": _build_control_deck_payload(self),
            }

    def _success(self, action_id: str, message: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": True,
            "actionId": action_id,
            "message": message,
            "payload": payload or {},
            "snapshot": _build_snapshot_payload(self),
        }

    def _start_auto_loop(self) -> str:
        if self.is_auto_running():
            return "이미 자동 감시가 실행 중입니다."

        persisted = self.store.load()
        persisted.runtime.clear_operator_pause()
        self.store.save(persisted)
        self._auto_stop_event.clear()
        self._auto_thread = threading.Thread(target=self._auto_loop_worker, daemon=True)
        self._auto_thread.start()
        message = "자동 감시를 시작했습니다."
        self.store.append_log(message)
        return message

    def _stop_auto_loop(self) -> None:
        if not self.is_auto_running():
            return
        self._auto_stop_event.set()
        if self._auto_thread is not None:
            self._auto_thread.join(timeout=1.5)
        self._auto_thread = None

    def _auto_loop_worker(self) -> None:
        while not self._auto_stop_event.is_set():
            wait_seconds = 5
            try:
                with self._lock:
                    persisted = self.store.load()
                    session = persisted.session
                    runtime = persisted.runtime
                    runtime.clear_operator_pause()
                    report = self.engine.run_cycle(session, runtime)
                    self.store.save(persisted)
                    self._append_report_logs(report)
                    wait_seconds = max(session.automation.poll_interval_sec, 1)
            except Exception as exc:
                self.store.append_log(f"[오류] web shell 자동 감시 실패: {exc}")

            for _ in range(wait_seconds * 10):
                if self._auto_stop_event.is_set():
                    break
                time.sleep(0.1)

        self.store.append_log("자동 감시를 멈췄습니다.")

    def _recent_log_lines(self, limit: int = 40) -> list[str]:
        if not self.store.log_path.exists():
            return []
        try:
            lines = self.store.log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        return lines[-limit:]

    def _activity_feed(self, limit: int = 18) -> list[dict[str, str]]:
        if not self.store.log_path.exists():
            return []
        try:
            lines = self.store.log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []

        items: list[dict[str, str]] = []
        for raw_line in reversed(lines):
            line = raw_line.rstrip()
            if not line.strip():
                continue

            timestamp = ""
            message = line.strip()
            if line.startswith("[") and "] " in line:
                stamp_text, _, rest = line.partition("] ")
                timestamp = stamp_text.lstrip("[")
                message = rest.strip()

            items.append(
                {
                    "timestamp": timestamp,
                    "message": message,
                    "tone": _activity_tone(message),
                }
            )
            if len(items) >= limit:
                break

        return items

    def _append_report_logs(self, report: Any) -> None:
        for line in self._report_log_lines(report):
            self.store.append_log(line)

    def _report_log_lines(self, report: Any) -> list[str]:
        lines = [self._format_report(report)]
        if getattr(report, "step_sent", None):
            lines.append(f"[프롬프트 기록]\n{report.step_sent}")
        return lines

    def _format_report(self, report: Any) -> str:
        parts = [report.message]
        if getattr(report, "step_index", None) is not None:
            parts.append(f"단계: {report.step_index + 1} {report.step_title or '-'}")
        if getattr(report, "window_title", ""):
            parts.append(f"창: {report.window_title}")
        if getattr(report, "lock_status", ""):
            parts.append(f"잠금 상태: {report.lock_status}")
        if getattr(report, "target_score", None) is not None:
            parts.append(f"타깃 점수: {report.target_score}")
        return " | ".join(parts)

    def _serialize_report(self, report: Any) -> dict[str, Any]:
        return {
            "message": report.message,
            "windowFound": report.window_found,
            "windowTitle": report.window_title,
            "stepIndex": report.step_index,
            "stepTitle": report.step_title,
            "lockStatus": report.lock_status,
            "actionTaken": report.action_taken,
            "stepSent": report.step_sent,
        }

    def _resolve_target(self, session: Any, runtime: Any) -> WindowResolution:
        resolution = self.bridge.resolve_target(session.window)
        self._sync_runtime_from_resolution(runtime, resolution)
        if resolution.selected is None:
            raise ValueError(resolution.summary())
        return resolution

    def _remember_resolution(self, session: Any, resolution: WindowResolution) -> None:
        if resolution.selected is None:
            return
        session.window.remember_success(
            handle=resolution.selected.handle,
            process_id=resolution.selected.process_id,
            title=resolution.selected.title,
            process_name=resolution.selected.process_name,
            score=resolution.score,
            reason=resolution.reason_text or resolution.summary(),
        )

    def _sync_runtime_from_resolution(self, runtime: Any, resolution: WindowResolution) -> None:
        runtime.last_target_title = resolution.selected.title if resolution.selected else ""
        runtime.last_target_reason = resolution.reason_text or resolution.summary()
        runtime.last_target_score = resolution.score if resolution.selected else None
        runtime.target_lock_status = resolution.lock_status

    def _build_status_summary(self, session: Any, runtime: Any) -> str:
        preview = self.engine.build_prompt_preview(session, runtime)
        queue = self.engine.build_step_queue(session, runtime)
        base_state = self.engine.build_surface_state(session, runtime, preview=preview, queue=queue)
        surface = self.engine.apply_judgment_surface_overlay(base_state, session, runtime, preview=preview)
        lines = [
            f"상태: {surface.badge_label}",
            f"현재: {surface.title}",
            f"요약: {surface.summary}",
            f"이유: {surface.reason}",
            f"다음 행동: {surface.next_action}",
            f"진행도: {surface.progress_label}",
            f"상세: {surface.detail_label}",
            f"위험: {surface.risk_label}",
        ]
        return "\n".join(lines)


def _build_snapshot_payload(service: LocalBridgeService) -> dict[str, Any]:
    persisted = service.store.load()
    session = persisted.session
    runtime = persisted.runtime
    runtime.auto_running = service.is_auto_running()

    queue = service.engine.build_step_queue(session, runtime)
    preview = service.engine.build_prompt_preview(session, runtime)
    surface = service.engine.build_surface_state(session, runtime, preview=preview, queue=queue)
    surface = service.engine.apply_judgment_surface_overlay(surface, session, runtime, preview=preview)

    steps = session.project.steps()
    total_steps = len(steps)
    next_index = min(max(runtime.next_step_index, 0), total_steps)
    current_step = steps[next_index] if next_index < total_steps else ""
    progress_ratio = 1.0 if total_steps == 0 else round(next_index / total_steps, 3)

    if not session.project.project_summary.strip():
        headline = "프로젝트 정보를 먼저 잡아주세요"
        summary = "아직 프로젝트 요약이 비어 있습니다. Python 엔진에서 세션을 저장하면 여기에 바로 반영됩니다."
        next_action = "프로젝트 요약과 단계 목록을 먼저 입력해 주세요."
        badge = "SETUP"
    elif runtime.operator_paused:
        headline = "운영이 보류 상태입니다"
        summary = runtime.operator_pause_reason or "운영자가 pause 상태로 둔 세션입니다."
        next_action = "보류 사유를 확인한 뒤 재개 또는 정책 조정을 선택해 주세요."
        badge = "PAUSED"
    elif total_steps == 0:
        headline = "단계 목록이 아직 준비되지 않았습니다"
        summary = "프로젝트 개요는 있지만 단계 목록이 비어 있습니다."
        next_action = "마스터플랜 단계들을 세션에 넣어 주세요."
        badge = "PLANNING"
    elif next_index >= total_steps:
        headline = "현재 저장된 단계는 모두 완료 상태입니다"
        summary = "다음 릴리즈나 새 프로젝트를 이어서 설계할 수 있습니다."
        next_action = "새 단계 묶음을 추가하거나 완료 보고 흐름으로 넘어가세요."
        badge = "DONE"
    else:
        headline = "다음 단계 진행 준비가 되어 있습니다"
        summary = f"현재 대기 단계는 {next_index + 1} / {total_steps} 입니다."
        next_action = current_step or "다음 단계 문구를 확인해 주세요."
        badge = "READY"

    recent_projects = []
    for item in persisted.recent_projects:
        recent_projects.append(
            {
                "title": item.project_summary or item.target_outcome or "이름 없는 프로젝트",
                "savedAt": item.saved_at,
                "progress": {
                    "current": item.next_step_index,
                    "total": item.total_steps,
                },
                "lastCapturePath": item.last_capture_path,
            }
        )

    surface_actions = [
        {
            "id": action.action_id,
            "label": action.label,
            "enabled": action.enabled,
            "emphasis": action.emphasis,
        }
        for action in surface.actions
    ]

    queue_items = [
        {
            "index": item.index,
            "total": item.total,
            "title": item.title,
            "status": item.status,
            "displayLine": item.display_line(),
        }
        for item in queue
    ]

    prompt_source = "draft" if preview.is_dirty else "generated"
    prompt_body = preview.draft_prompt or preview.generated_prompt

    deck_sections = [
        {
            "id": "project",
            "title": "Project",
            "value": session.project.project_summary or "세션 대기",
            "description": session.project.target_outcome or "프로젝트 목표가 아직 없습니다.",
            "tone": _tone_for_flag(
                ready=bool(session.project.project_summary.strip() and session.project.steps_text.strip()),
                warning=not bool(session.project.steps_text.strip()),
            ),
        },
        {
            "id": "strategy",
            "title": "Codex Strategy",
            "value": session.codex_strategy.selected_preset_id or "recommended",
            "description": session.codex_strategy.selected_mode_id or "recommended",
            "tone": "good",
        },
        {
            "id": "judgment",
            "title": "Judgment",
            "value": session.judgment.engine_mode_id,
            "description": session.judgment.model_name,
            "tone": "good" if session.judgment.engine_mode_id != "off" else "muted",
        },
        {
            "id": "visual",
            "title": "Visual",
            "value": session.visual.target_mode_id,
            "description": session.visual.capture_scope_id,
            "tone": "good" if session.visual.target_mode_id != "off" else "muted",
        },
        {
            "id": "voice",
            "title": "Voice",
            "value": session.voice.language_code,
            "description": "brief on" if session.voice.auto_brief_enabled else "brief off",
            "tone": "good" if session.voice.spoken_feedback_enabled else "muted",
        },
        {
            "id": "Live Ops",
            "title": "Live Ops",
            "value": session.live_ops.selected_profile_id,
            "description": session.live_ops.report_cadence_id,
            "tone": "good",
        },
    ]

    signals = [
        {
            "label": "Codex Target",
            "value": runtime.last_target_title or "미연결",
            "tone": _tone_for_flag(ready=bool(runtime.last_target_title.strip())),
        },
        {
            "label": "Lock Status",
            "value": runtime.target_lock_status or "상태 없음",
            "tone": _tone_for_flag(ready=bool(runtime.target_lock_status.strip())),
        },
        {
            "label": "Judgment",
            "value": runtime.last_judgment.decision or "pending",
            "tone": _tone_for_flag(
                ready=runtime.last_judgment.decision in {"continue", "wait"},
                warning=runtime.last_judgment.decision in {"pause", "ask_user", "retry"},
            ),
        },
        {
            "label": "Loop Mode",
            "value": "auto" if runtime.auto_running else ("dry run" if session.automation.dry_run else "manual"),
            "tone": "good" if runtime.auto_running else ("muted" if session.automation.dry_run else "good"),
        },
    ]

    return {
        "generatedAt": _now_iso(),
        "app": {
            "name": "javis",
            "ui": "web-shell",
            "engine": "python",
        },
        "project": {
            "summary": session.project.project_summary,
            "targetOutcome": session.project.target_outcome,
            "steps": steps,
        },
        "assistant": {
            "badge": badge,
            "headline": headline,
            "summary": summary,
            "nextAction": next_action,
        },
        "surface": {
            "stateKey": surface.state_key,
            "projectLabel": surface.project_label,
            "badgeLabel": surface.badge_label,
            "title": surface.title,
            "summary": surface.summary,
            "reason": surface.reason,
            "nextAction": surface.next_action,
            "progressLabel": surface.progress_label,
            "detailLabel": surface.detail_label,
            "riskLabel": surface.risk_label,
            "actions": surface_actions,
        },
        "runtime": {
            "savedAt": persisted.saved_at,
            "progress": {
                "current": next_index,
                "total": total_steps,
                "ratio": progress_ratio,
            },
            "currentStep": current_step,
            "lastCapturePath": runtime.last_capture_path,
            "lastTargetTitle": runtime.last_target_title,
            "lockStatus": runtime.target_lock_status,
            "operatorPaused": runtime.operator_paused,
            "operatorPauseReason": runtime.operator_pause_reason,
            "autoRunning": runtime.auto_running,
        },
        "codex": {
            "strategyPresetId": session.codex_strategy.selected_preset_id,
            "automationModeId": session.codex_strategy.selected_mode_id,
            "deepIntegrationModeId": session.deep_integration.selected_mode_id,
            "liveOpsProfileId": session.live_ops.selected_profile_id,
        },
        "queue": queue_items,
        "promptPreview": {
            "hasStep": preview.has_step,
            "isComplete": preview.is_complete,
            "stepIndex": preview.step_index,
            "stepTitle": preview.step_title,
            "source": prompt_source,
            "excerpt": _excerpt(prompt_body),
            "generatedPrompt": preview.generated_prompt,
            "draftPrompt": preview.draft_prompt,
        },
        "signals": signals,
        "deckSections": deck_sections,
        "recentProjects": recent_projects,
    }


def _build_control_deck_payload(service: LocalBridgeService) -> dict[str, Any]:
    persisted = service.store.load()
    session = persisted.session
    runtime = persisted.runtime

    preview = service.engine.build_prompt_preview(session, runtime)
    launch_prompt = service.engine.build_codex_strategy_prompt(session, runtime)
    runbook = service.engine.build_codex_strategy_runbook(session, runtime)
    runboard = service.engine.build_automation_runboard(session, runtime)
    shift_brief = service.engine.build_live_ops_shift_brief(session, runtime)
    judgment_timeline = service.engine.build_judgment_timeline(runtime)
    visual_timeline = service.engine.build_visual_timeline(runtime)
    voice_timeline = service.engine.build_voice_timeline(runtime)
    capability_registry = service.engine.build_deep_integration_capability_registry(session, runtime)
    cross_surface_handoff = service.engine.build_cross_surface_handoff_bundle(session, runtime)
    observability_report = service.engine.build_integration_observability_report(session, runtime)

    recent_projects = []
    for index, item in enumerate(persisted.recent_projects):
        recent_projects.append(
            {
                "index": index,
                "title": item.project_summary or item.target_outcome or "이름 없는 프로젝트",
                "targetOutcome": item.target_outcome,
                "savedAt": item.saved_at,
                "progress": {
                    "current": item.next_step_index,
                    "total": item.total_steps,
                },
                "lastCapturePath": item.last_capture_path,
            }
        )

    return {
        "projectEditor": {
            "projectSummary": session.project.project_summary,
            "targetOutcome": session.project.target_outcome,
            "stepsText": session.project.steps_text,
            "stepCount": len(session.project.steps()),
            "nextStepIndex": runtime.next_step_index,
        },
        "operationsEditor": {
            "codexStrategy": {
                "selectedPresetId": session.codex_strategy.selected_preset_id,
                "selectedModeId": session.codex_strategy.selected_mode_id,
                "customInstruction": session.codex_strategy.custom_instruction,
                "presetOptions": [
                    _option_payload(option.preset_id, option.title, option.summary) for option in CODEX_AUTOMATION_PRESETS
                ],
                "modeOptions": [
                    _option_payload(option.mode_id, option.title, option.summary) for option in CODEX_AUTOMATION_MODE_OPTIONS
                ],
            },
            "automation": {
                "pollIntervalSec": session.automation.poll_interval_sec,
                "dryRun": session.automation.dry_run,
            },
            "liveOps": {
                "selectedProfileId": session.live_ops.selected_profile_id,
                "reportCadenceId": session.live_ops.report_cadence_id,
                "reentryModeId": session.live_ops.reentry_mode_id,
                "operatorNote": session.live_ops.operator_note,
                "profileOptions": [
                    _option_payload(option.profile_id, option.title, option.summary) for option in LIVE_OPS_PROFILE_OPTIONS
                ],
                "cadenceOptions": [
                    _option_payload(option.cadence_id, option.title, option.summary)
                    for option in LIVE_OPS_REPORT_CADENCE_OPTIONS
                ],
                "reentryOptions": [
                    _option_payload(option.reentry_id, option.title, option.summary) for option in LIVE_OPS_REENTRY_OPTIONS
                ],
            },
        },
        "promptWorkbench": {
            "hasStep": preview.has_step,
            "stepIndex": preview.step_index,
            "stepTitle": preview.step_title,
            "source": preview.source_label,
            "generatedPrompt": preview.generated_prompt,
            "draftPrompt": preview.draft_prompt,
            "isDirty": preview.is_dirty,
        },
        "intelligenceStudio": {
            "judgment": {
                "engineModeId": session.judgment.engine_mode_id,
                "modelName": session.judgment.model_name,
                "confidenceThreshold": session.judgment.confidence_threshold,
                "maxHistoryItems": session.judgment.max_history_items,
                "modeOptions": [
                    _option_payload(option.mode_id, option.title, option.summary) for option in JUDGMENT_ENGINE_MODE_OPTIONS
                ],
                "timeline": judgment_timeline,
                "historyLines": [item.display_line() for item in runtime.judgment_history],
                "lastResult": {
                    "decision": runtime.last_judgment.decision,
                    "reason": runtime.last_judgment.reason,
                    "confidence": runtime.last_judgment.confidence,
                    "riskLevel": runtime.last_judgment.risk_level,
                    "messageToUser": runtime.last_judgment.message_to_user,
                    "source": runtime.last_judgment.source,
                    "evaluatedAt": runtime.last_judgment.evaluated_at,
                    "validationNotes": runtime.last_judgment.validation_notes,
                },
            },
            "visual": {
                "targetModeId": session.visual.target_mode_id,
                "captureScopeId": session.visual.capture_scope_id,
                "retentionHintId": session.visual.retention_hint_id,
                "sensitiveContentRisk": session.visual.sensitive_content_risk,
                "expectedPage": session.visual.expected_page,
                "expectedSignalsText": session.visual.expected_signals_text,
                "disallowedSignalsText": session.visual.disallowed_signals_text,
                "observationFocusText": session.visual.observation_focus_text,
                "observedNotesText": session.visual.observed_notes_text,
                "targetModeOptions": [
                    _option_payload(option.mode_id, option.title, option.summary) for option in VISUAL_TARGET_MODE_OPTIONS
                ],
                "captureScopeOptions": [
                    _option_payload(option.scope_id, option.title, option.summary)
                    for option in VISUAL_CAPTURE_SCOPE_OPTIONS
                ],
                "retentionOptions": [
                    _option_payload(option.retention_id, option.title, option.summary) for option in VISUAL_RETENTION_OPTIONS
                ],
                "timeline": visual_timeline,
                "historyLines": [item.display_line() for item in runtime.visual_history],
                "lastResult": {
                    "targetLabel": runtime.last_visual_result.target_label,
                    "contradictionLevel": runtime.last_visual_result.contradiction_level,
                    "decisionHint": runtime.last_visual_result.decision_hint,
                    "messageToUser": runtime.last_visual_result.message_to_user,
                    "observedSummary": runtime.last_visual_result.observed_summary,
                    "evaluatedAt": runtime.last_visual_result.evaluated_at,
                },
            },
            "voice": {
                "languageCode": session.voice.language_code,
                "autoBriefEnabled": session.voice.auto_brief_enabled,
                "confirmationEnabled": session.voice.confirmation_enabled,
                "spokenFeedbackEnabled": session.voice.spoken_feedback_enabled,
                "ambientReadyEnabled": session.voice.ambient_ready_enabled,
                "microphoneName": session.voice.microphone_name,
                "speakerName": session.voice.speaker_name,
                "timeline": voice_timeline,
                "historyLines": [item.display_line() for item in runtime.voice_history],
                "lastResult": {
                    "transcriptText": runtime.last_voice_result.transcript_text,
                    "intentId": runtime.last_voice_result.normalized_intent_id,
                    "actionStatus": runtime.last_voice_result.action_status,
                    "messageToUser": runtime.last_voice_result.message_to_user,
                    "spokenBriefingText": runtime.last_voice_result.spoken_briefing_text,
                    "evaluatedAt": runtime.last_voice_result.evaluated_at,
                },
            },
            "deepIntegration": {
                "selectedModeId": session.deep_integration.selected_mode_id,
                "appServerReadinessId": session.deep_integration.app_server_readiness_id,
                "cloudTriggerReadinessId": session.deep_integration.cloud_trigger_readiness_id,
                "desktopFallbackAllowed": session.deep_integration.desktop_fallback_allowed,
                "appServerNotes": session.deep_integration.app_server_notes,
                "cloudTriggerNotes": session.deep_integration.cloud_trigger_notes,
                "handoffNotes": session.deep_integration.handoff_notes,
                "modeOptions": [
                    _option_payload(option.mode_id, option.title, option.summary) for option in DEEP_INTEGRATION_MODE_OPTIONS
                ],
                "readinessOptions": [
                    _option_payload(option.readiness_id, option.title, option.summary)
                    for option in DEEP_INTEGRATION_READINESS_OPTIONS
                ],
                "capabilityRegistry": capability_registry,
                "crossSurfaceHandoff": cross_surface_handoff,
                "observabilityReport": observability_report,
            },
        },
        "runbooks": {
            "launchPrompt": launch_prompt,
            "runbook": runbook,
            "runboard": runboard,
            "shiftBrief": shift_brief,
        },
        "recentProjects": recent_projects,
    }


def _build_workspace_bundle_payload(service: LocalBridgeService) -> dict[str, Any]:
    return {
        "generatedAt": _now_iso(),
        "snapshot": _build_snapshot_payload(service),
        "controlDeck": _build_control_deck_payload(service),
        "activityFeed": service._activity_feed(),
    }


class SnapshotRequestHandler(BaseHTTPRequestHandler):
    service: LocalBridgeService

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT.value)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": "javis-local-api",
                    "generatedAt": _now_iso(),
                },
            )
            return

        if self.path == "/api/snapshot":
            self._send_json(HTTPStatus.OK, self.service.build_snapshot())
            return

        if self.path == "/api/control-deck":
            self._send_json(HTTPStatus.OK, self.service.build_control_deck())
            return

        if self.path == "/api/workspace":
            self._send_json(HTTPStatus.OK, self.service.build_workspace_bundle())
            return

        self._send_json(
            HTTPStatus.NOT_FOUND,
            {
                "status": "not_found",
                "path": self.path,
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/api/action", "/api/control-deck"}:
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {
                    "status": "not_found",
                    "path": self.path,
                },
            )
            return

        content_length = int(self.headers.get("Content-Length", "0") or 0)
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "유효한 JSON 요청이 아닙니다."})
            return

        if self.path == "/api/action":
            action_id = str(payload.get("actionId", "")).strip()
            if not action_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "actionId가 필요합니다."})
                return

            try:
                response = self.service.perform_action(action_id)
                self._send_json(HTTPStatus.OK, response)
            except Exception as exc:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "ok": False,
                        "actionId": action_id,
                        "message": str(exc),
                        "snapshot": self.service.build_snapshot(),
                    },
                )
            return

        kind = str(payload.get("kind", "")).strip()
        if not kind:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "kind가 필요합니다."})
            return

        try:
            response = self.service.update_control_deck(kind, payload)
            self._send_json(HTTPStatus.OK, response)
        except Exception as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "kind": kind,
                    "message": str(exc),
                    "snapshot": self.service.build_snapshot(),
                    "controlDeck": self.service.build_control_deck(),
                },
            )

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(host: str, port: int, workspace: Path) -> None:
    service = LocalBridgeService(workspace)
    handler_class = type(
        "BoundSnapshotRequestHandler",
        (SnapshotRequestHandler,),
        {"service": service},
    )
    server = ThreadingHTTPServer((host, port), handler_class)
    try:
        print(f"javis local api listening on http://{host}:{port}")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.shutdown()
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the javis local API for the web shell.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workspace", default=str(Path.cwd()))
    parser.add_argument("--dump-snapshot", action="store_true")
    parser.add_argument("--dump-control-deck", action="store_true")
    parser.add_argument("--dump-workspace", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if args.dump_snapshot:
        service = LocalBridgeService(workspace)
        print(json.dumps(service.build_snapshot(), ensure_ascii=False, indent=2))
        service.shutdown()
        return
    if args.dump_control_deck:
        service = LocalBridgeService(workspace)
        print(json.dumps(service.build_control_deck(), ensure_ascii=False, indent=2))
        service.shutdown()
        return
    if args.dump_workspace:
        service = LocalBridgeService(workspace)
        print(json.dumps(service.build_workspace_bundle(), ensure_ascii=False, indent=2))
        service.shutdown()
        return
    serve(args.host, args.port, workspace)


if __name__ == "__main__":
    main()
