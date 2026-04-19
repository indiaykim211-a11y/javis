from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.automation.bmp import compute_signature, normalized_distance
from app.automation.windows_ui import WindowResolution, WindowsDesktopBridge
from app.models import (
    CodexAutomationModeDecision,
    CycleReport,
    DeepIntegrationModeDecision,
    JudgmentResult,
    LiveOpsStatusDecision,
    PopupActionModel,
    PromptPreview,
    RuntimeState,
    SessionConfig,
    SurfaceStateModel,
    StepQueueItem,
    VisualEvidenceResult,
    VoiceCommandResult,
    get_codex_automation_mode_option,
    get_codex_automation_preset,
    get_deep_integration_mode_option,
    get_deep_integration_readiness_option,
    get_live_ops_profile_option,
    get_live_ops_reentry_option,
    get_live_ops_report_cadence_option,
    get_visual_capture_scope_option,
    get_visual_retention_option,
    get_visual_target_mode_option,
)


class AutomationEngine:
    def __init__(self, bridge: WindowsDesktopBridge, capture_dir: Path) -> None:
        self.bridge = bridge
        self.capture_dir = capture_dir

    def build_step_queue(self, session: SessionConfig, runtime: RuntimeState) -> list[StepQueueItem]:
        steps = session.project.steps()
        items: list[StepQueueItem] = []
        for index, step in enumerate(steps):
            if index < runtime.next_step_index:
                status = "done"
            elif index == runtime.next_step_index:
                status = "current"
            elif index == runtime.next_step_index + 1:
                status = "next"
            else:
                status = "upcoming"
            items.append(
                StepQueueItem(
                    index=index,
                    total=len(steps),
                    title=step,
                    status=status,
                )
            )
        return items

    def build_prompt_preview(self, session: SessionConfig, runtime: RuntimeState) -> PromptPreview:
        steps = session.project.steps()
        total = len(steps)
        if runtime.next_step_index >= total:
            runtime.clear_prompt_preview()
            return PromptPreview(total_steps=total, is_complete=True)

        step_index = runtime.next_step_index
        generated_prompt = self.build_step_prompt(session, step_index)
        runtime.sync_prompt_preview(step_index, generated_prompt)
        return PromptPreview(
            step_index=step_index,
            total_steps=total,
            step_title=steps[step_index],
            generated_prompt=generated_prompt,
            draft_prompt=runtime.prompt_draft,
            is_dirty=runtime.prompt_dirty,
        )

    def build_capture_target_plan(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        recent_log_lines: list[str] | None = None,
    ) -> dict[str, Any]:
        mode = session.visual.target_mode()
        logs = [line.strip() for line in (recent_log_lines or []) if line.strip()]
        lowered = "\n".join(logs).lower()
        effective_target = mode.mode_id

        if mode.mode_id == "auto":
            browser_hints = ("browser", "page", "ui", "route", "render", "버튼", "브라우저", "페이지", "cta")
            if session.visual.expected_page.strip() or any(hint in lowered for hint in browser_hints):
                effective_target = "browser_result"
                reason = "현재 기대 페이지나 최근 로그가 브라우저 결과 확인 쪽에 더 가깝습니다."
            else:
                effective_target = "codex_window"
                reason = "최근 판단과 현재 캡처 기준으로는 Codex 창 상태를 먼저 읽는 편이 더 자연스럽습니다."
        elif mode.mode_id == "browser_result":
            reason = "브라우저 결과 화면을 우선 관찰하도록 수동 고정했습니다."
        else:
            reason = "Codex 창을 우선 관찰하도록 수동 고정했습니다."

        target_label = "브라우저 결과 화면" if effective_target == "browser_result" else "Codex 창"
        region_label = "main browser viewport" if effective_target == "browser_result" else "codex main window"
        priority = "high" if runtime.last_judgment.decision in {"continue", "retry", "ask_user"} else "medium"
        trigger = "claim_screen_mismatch" if runtime.last_judgment.decision == "continue" else "visual_follow_up"

        return {
            "requested_mode": mode.mode_id,
            "effective_target_type": effective_target,
            "target_label": target_label,
            "region_label": region_label,
            "capture_reason": reason,
            "priority": priority,
            "trigger": trigger,
            "requested_by": "javis",
        }

    def build_visual_evidence_packet(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        recent_log_lines: list[str] | None = None,
    ) -> dict[str, Any]:
        preview = self.build_prompt_preview(session, runtime)
        plan = self.build_capture_target_plan(session, runtime, recent_log_lines)
        scope = session.visual.capture_scope()
        retention = session.visual.retention_hint()
        focus = session.visual.observation_focus() or [
            "오류 배너 존재 여부",
            "핵심 CTA 존재 여부",
            "빈 화면 또는 잘못된 라우팅 여부",
            "Codex 주장과 모순되는 신호",
        ]

        screen_targets = []
        if runtime.last_capture_path:
            screen_targets.append(
                {
                    "target_type": plan["effective_target_type"],
                    "path": runtime.last_capture_path,
                    "region_label": plan["region_label"],
                    "why_this_target": plan["capture_reason"],
                }
            )

        return {
            "capture_plan": {
                "capture_reason": plan["capture_reason"],
                "priority": plan["priority"],
                "trigger": plan["trigger"],
                "requested_by": plan["requested_by"],
            },
            "expected_state": {
                "current_step_title": preview.step_title or "현재 단계 없음",
                "expected_page": session.visual.expected_page.strip() or "현재 단계에 맞는 정상 화면",
                "expected_signals": session.visual.expected_signals(),
                "disallowed_signals": session.visual.disallowed_signals(),
            },
            "observation_focus": focus,
            "screen_targets": screen_targets,
            "judgment_bridge": {
                "current_decision_before_visual": runtime.last_judgment.decision or "none",
                "why_visual_is_needed": (
                    "텍스트와 네이티브 결과만으로는 실제 화면 상태 확인이 부족하거나, 현재 판단과 모순 가능성이 있기 때문입니다."
                ),
                "question_to_resolve": "Codex 주장과 실제 화면이 일치하는가",
                "candidate_outcomes": ["continue", "retry", "ask_user", "pause"],
            },
            "safety": {
                "capture_scope": scope.scope_id,
                "capture_scope_label": scope.title,
                "sensitive_content_risk": session.visual.sensitive_content_risk,
                "retention_hint": retention.retention_id,
                "retention_label": retention.title,
                "fallback_if_uncertain": "ask_user",
            },
            "observed_notes": session.visual.observed_notes_text.strip(),
            "target_meta": plan,
        }

    def serialize_visual_evidence_packet(self, packet: dict[str, Any]) -> str:
        return json.dumps(packet, ensure_ascii=False, indent=2)

    def build_visual_observation_prompt(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        *,
        packet: dict[str, Any] | None = None,
    ) -> str:
        active_packet = packet if packet is not None else self.build_visual_evidence_packet(session, runtime)
        packet_text = self.serialize_visual_evidence_packet(active_packet)
        target_type = active_packet.get("target_meta", {}).get("effective_target_type", "codex_window")
        target_label = "브라우저 결과 화면" if target_type == "browser_result" else "Codex 창"
        return "\n".join(
            [
                f"당신은 javis의 {target_label} 관찰 보조 엔진입니다.",
                "설명 자체보다 판정에 필요한 시각 신호를 짧게 정리해 주세요.",
                "",
                "[관찰 원칙]",
                "- 오류 배너, 빈 화면, CTA 부재, 잘못된 라우팅, Codex 주장과 모순되는 신호를 먼저 봅니다.",
                "- 정상처럼 보여도 확신이 낮으면 추정이라고 적고 ask_user 쪽을 우선합니다.",
                "- 전체 화면 설명보다 현재 단계와 직접 관련 있는 근거만 남깁니다.",
                "",
                "[기대 화면 / 금지 신호]",
                f"- 기대 페이지: {session.visual.expected_page.strip() or '현재 단계에 맞는 정상 화면'}",
                f"- 기대 신호: {', '.join(session.visual.expected_signals()) or '미입력'}",
                f"- 금지 신호: {', '.join(session.visual.disallowed_signals()) or '미입력'}",
                "",
                "[출력 원칙]",
                "- observed_summary를 짧게 만들고, contradiction 여부를 먼저 판정합니다.",
                "- contradiction가 보이면 어떤 신호가 문제인지 바로 적습니다.",
                "",
                "[Visual Evidence Packet]",
                packet_text,
            ]
        ).strip()

    def detect_visual_contradiction(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        *,
        packet: dict[str, Any] | None = None,
        recent_log_lines: list[str] | None = None,
    ) -> VisualEvidenceResult:
        active_packet = packet if packet is not None else self.build_visual_evidence_packet(session, runtime, recent_log_lines)
        target_meta = active_packet.get("target_meta", {})
        target_type = target_meta.get("effective_target_type", "codex_window")
        target_label = target_meta.get("target_label", "화면")
        observed_text = active_packet.get("observed_notes", "").strip()
        log_text = "\n".join(line.strip() for line in (recent_log_lines or []) if line.strip())
        combined = "\n".join(part for part in [observed_text, log_text] if part).lower()

        expected_page = active_packet.get("expected_state", {}).get("expected_page", "")
        expected_signals = active_packet.get("expected_state", {}).get("expected_signals", [])
        disallowed_signals = active_packet.get("expected_state", {}).get("disallowed_signals", [])

        mismatch_signals: list[str] = []
        for signal in disallowed_signals:
            if signal and signal.lower() in combined:
                mismatch_signals.append(signal)

        keyword_map = {
            "빈 화면": "빈 화면",
            "blank": "빈 화면",
            "오류 배너": "오류 배너",
            "error": "오류 신호",
            "에러": "오류 신호",
            "404": "잘못된 라우팅",
            "cta 없음": "CTA 없음",
            "버튼 없음": "핵심 버튼 없음",
            "missing button": "핵심 버튼 없음",
            "wrong route": "잘못된 라우팅",
            "잘못된 라우팅": "잘못된 라우팅",
        }
        for keyword, label in keyword_map.items():
            if keyword in combined and label not in mismatch_signals:
                mismatch_signals.append(label)

        contradiction_detected = bool(mismatch_signals)
        contradiction_level = "none"
        decision_hint = "continue"
        contradiction_reason = "현재 관찰 메모와 최근 로그 기준으로 뚜렷한 화면 모순은 보이지 않습니다."
        message_to_user = "현재 시각 근거 기준으로는 큰 모순이 보이지 않습니다."

        severe_signals = {"빈 화면", "잘못된 라우팅", "오류 배너", "오류 신호"}
        if contradiction_detected:
            contradiction_level = "high" if any(signal in severe_signals for signal in mismatch_signals) else "medium"
            if contradiction_level == "high":
                decision_hint = "ask_user"
                contradiction_reason = "Codex 주장과 실제 화면 사이에 큰 모순 또는 실패 신호가 보여 상단장님 확인이 우선입니다."
                message_to_user = "화면에서 큰 모순 신호가 보여 바로 진행하지 않고 확인이 필요합니다."
            else:
                decision_hint = "retry"
                contradiction_reason = "화면에서 현재 단계와 어긋나는 신호가 보여 같은 단계를 보정해 다시 시도하는 편이 안전합니다."
                message_to_user = "화면 모순이 보여 같은 단계를 보정해서 다시 시도하는 편이 좋습니다."
        elif not observed_text and not runtime.last_capture_path:
            contradiction_level = "low"
            decision_hint = "pause"
            contradiction_reason = "시각 근거가 아직 없어 화면 판독을 진행하기 전에 캡처나 관찰 메모가 더 필요합니다."
            message_to_user = "아직 시각 근거가 부족해 잠시 멈추고 캡처를 더 확인하는 편이 좋습니다."
        elif "확신 낮" in combined or "uncertain" in combined:
            contradiction_level = "medium"
            decision_hint = "ask_user"
            contradiction_reason = "화면 관찰 확신이 낮아 continue보다 ask_user가 안전합니다."
            message_to_user = "화면 근거 확신이 낮아 확인이 필요합니다."

        evidence_summary = [
            f"타깃: {target_label}",
            f"기대 페이지: {expected_page or '미입력'}",
            f"기대 신호: {', '.join(expected_signals) if expected_signals else '미입력'}",
            f"관찰 메모: {observed_text or '미입력'}",
        ]
        if mismatch_signals:
            evidence_summary.append(f"mismatch 신호: {', '.join(mismatch_signals)}")
        if runtime.last_capture_path:
            evidence_summary.append(f"최근 캡처: {Path(runtime.last_capture_path).name}")

        return VisualEvidenceResult(
            target_type=target_type,
            target_label=target_label,
            contradiction_detected=contradiction_detected,
            contradiction_level=contradiction_level,
            contradiction_reason=contradiction_reason,
            expected_summary=expected_page or "현재 단계에 맞는 정상 화면",
            observed_summary=observed_text or "관찰 메모 미입력",
            decision_hint=decision_hint,
            message_to_user=message_to_user,
            evidence_summary=evidence_summary,
            mismatch_signals=mismatch_signals,
            source="visual_rule_based",
            evaluated_at=datetime.now().isoformat(timespec="seconds"),
        )

    def format_visual_evidence_result(self, result: VisualEvidenceResult) -> str:
        return json.dumps(
            {
                "target_type": result.target_type,
                "target_label": result.target_label,
                "contradiction_detected": result.contradiction_detected,
                "contradiction_level": result.contradiction_level,
                "contradiction_reason": result.contradiction_reason,
                "expected_summary": result.expected_summary,
                "observed_summary": result.observed_summary,
                "decision_hint": result.decision_hint,
                "message_to_user": result.message_to_user,
                "evidence_summary": result.evidence_summary,
                "mismatch_signals": result.mismatch_signals,
                "source": result.source,
                "evaluated_at": result.evaluated_at,
            },
            ensure_ascii=False,
            indent=2,
        )

    def build_visual_timeline(self, runtime: RuntimeState) -> str:
        lines = ["[Visual Timeline]"]
        if runtime.last_visual_result.has_result:
            result = runtime.last_visual_result
            lines.extend(
                [
                    f"최근 시각 판단: {result.target_label or result.target_type} | contradiction {result.contradiction_level} | hint {result.decision_hint}",
                    f"기대 화면: {result.expected_summary}",
                    f"관찰 요약: {result.observed_summary}",
                    f"판정 이유: {result.contradiction_reason}",
                ]
            )
            if result.evidence_summary:
                lines.extend(["", "[시각 근거 요약]"])
                lines.extend(f"- {item}" for item in result.evidence_summary)
            if result.mismatch_signals:
                lines.extend(["", "[mismatch 신호]"])
                lines.extend(f"- {item}" for item in result.mismatch_signals)
        else:
            lines.append("아직 저장된 시각 판단 결과가 없습니다.")

        lines.extend(["", "[최근 시각 이력]"])
        if runtime.visual_history:
            lines.extend(f"- {item.display_line()}" for item in runtime.visual_history)
        else:
            lines.append("- 시각 판단 이력이 아직 없습니다.")
        return "\n".join(lines).strip()

    def run_visual_rejudge(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        *,
        recent_log_lines: list[str] | None = None,
    ) -> tuple[VisualEvidenceResult, JudgmentResult]:
        visual_packet = self.build_visual_evidence_packet(session, runtime, recent_log_lines)
        visual_prompt = self.build_visual_observation_prompt(session, runtime, packet=visual_packet)
        visual_result = self.detect_visual_contradiction(
            session,
            runtime,
            packet=visual_packet,
            recent_log_lines=recent_log_lines,
        )
        visual_summary = self.format_visual_evidence_result(visual_result)
        runtime.remember_visual_result(
            visual_result,
            packet_text=self.serialize_visual_evidence_packet(visual_packet),
            prompt_text=visual_prompt,
            summary_text=visual_summary,
            max_history_items=session.judgment.max_history_items,
        )

        visual_context = {
            "packet": visual_packet,
            "result": visual_result.to_dict(),
        }
        judgment_result = self.run_judgment(
            session,
            runtime,
            recent_log_lines=recent_log_lines,
            visual_context=visual_context,
        )
        return visual_result, judgment_result

    def build_voice_briefing(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        *,
        intent_id: str = "status_summary",
    ) -> str:
        preview = self.build_prompt_preview(session, runtime)
        queue = self.build_step_queue(session, runtime)
        base_state = self.build_surface_state(session, runtime, preview=preview, queue=queue)
        surface = self.apply_judgment_surface_overlay(base_state, session, runtime, preview=preview)

        if intent_id == "why_paused":
            if runtime.operator_paused:
                pause_reason = runtime.operator_pause_reason or surface.reason or "명확한 보류 이유는 아직 남지 않았습니다."
                return " ".join(
                    [
                        "지금은 보류 상태입니다.",
                        f"이유는 {pause_reason}",
                        f"다음 행동은 {surface.next_action or '설정이나 판단 결과를 다시 확인하는 것'}입니다.",
                    ]
                ).strip()
            return "지금은 보류 상태가 아닙니다. 현재 흐름은 계속 진행 가능한지 다시 확인 중입니다."

        if intent_id == "read_last_judgment":
            if runtime.last_judgment.has_result:
                result = runtime.last_judgment
                return " ".join(
                    [
                        f"마지막 판단은 {result.decision}입니다.",
                        f"이유는 {result.reason or '명시된 이유 없음'}입니다.",
                        f"운영자에게는 {result.message_to_user or result.reason or '추가 메시지 없음'}으로 보고합니다.",
                    ]
                ).strip()
            return "아직 저장된 마지막 판단 결과가 없습니다."

        if intent_id == "read_last_visual":
            if runtime.last_visual_result.has_result:
                result = runtime.last_visual_result
                return " ".join(
                    [
                        f"마지막 시각 판단은 contradiction {result.contradiction_level}입니다.",
                        f"관찰 요약은 {result.observed_summary or '관찰 메모 없음'}입니다.",
                        f"다음 힌트는 {result.decision_hint or 'continue'}입니다.",
                    ]
                ).strip()
            return "아직 저장된 시각 판단 결과가 없습니다."

        if intent_id == "repeat_briefing" and runtime.voice_last_briefing.strip():
            return runtime.voice_last_briefing.strip()

        if intent_id == "pause_run":
            return " ".join(
                [
                    "지금은 진행을 보류하겠습니다.",
                    f"현재 상태는 {surface.summary or surface.title}입니다.",
                    f"필요하면 {surface.next_action or '상태 요약을 다시 확인'}할 수 있습니다.",
                ]
            ).strip()

        if intent_id == "continue_step":
            return " ".join(
                [
                    f"현재 상태는 {surface.summary or surface.title}입니다.",
                    f"다음 행동은 {surface.next_action or '다음 단계를 진행하는 것'}입니다.",
                    "계속 진행 요청으로 이해했습니다.",
                ]
            ).strip()

        if intent_id == "open_settings":
            return "설정 창을 열겠습니다. 필요한 정책이나 운영 상태를 여기서 바로 확인할 수 있습니다."

        return " ".join(
            [
                f"현재 상태는 {surface.badge_label}입니다.",
                f"{surface.summary or surface.title}",
                f"이유는 {surface.reason or '추가 이유 없음'}입니다.",
                f"다음 행동은 {surface.next_action or '상태를 계속 관찰하는 것'}입니다.",
            ]
        ).strip()

    def build_voice_timeline(self, runtime: RuntimeState) -> str:
        lines = ["[Voice Timeline]"]
        if runtime.last_voice_result.has_result:
            result = runtime.last_voice_result
            lines.extend(
                [
                    f"마지막 voice intent: {result.normalized_intent_id or 'unknown'} | status {result.action_status or 'none'} | conf {result.intent_confidence:.2f}",
                    f"transcript: {result.transcript_text or '없음'}",
                    f"message: {result.message_to_user or '없음'}",
                    f"spoken briefing: {result.spoken_briefing_text or '없음'}",
                ]
            )
        else:
            lines.append("아직 저장된 voice 결과가 없습니다.")

        if runtime.voice_pending_action_id:
            lines.extend(
                [
                    "",
                    "[Pending Confirmation]",
                    f"- action: {runtime.voice_pending_action_id}",
                    f"- note: {runtime.voice_pending_confirmation_text or '없음'}",
                ]
            )

        lines.extend(["", "[Recent Voice History]"])
        if runtime.voice_history:
            lines.extend(f"- {item.display_line()}" for item in runtime.voice_history)
        else:
            lines.append("- voice history가 아직 없습니다.")
        return "\n".join(lines).strip()

    def interpret_voice_command(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        transcript_text: str,
    ) -> VoiceCommandResult:
        transcript = transcript_text.strip()
        lowered = transcript.lower()
        now = datetime.now().isoformat(timespec="seconds")

        preview = self.build_prompt_preview(session, runtime)
        queue = self.build_step_queue(session, runtime)
        base_state = self.build_surface_state(session, runtime, preview=preview, queue=queue)
        surface = self.apply_judgment_surface_overlay(base_state, session, runtime, preview=preview)

        def build_result(
            *,
            intent_id: str,
            confidence: float,
            action_id: str = "",
            action_status: str,
            message: str,
            briefing: str,
            clarification_question: str = "",
            requires_confirmation: bool = False,
        ) -> VoiceCommandResult:
            return VoiceCommandResult(
                transcript_text=transcript,
                normalized_intent_id=intent_id,
                intent_confidence=confidence,
                action_id=action_id,
                action_status=action_status,
                message_to_user=message,
                spoken_briefing_text=briefing,
                clarification_question=clarification_question,
                requires_confirmation=requires_confirmation,
                source="voice_rule_based",
                evaluated_at=now,
            )

        if not transcript:
            return build_result(
                intent_id="clarify",
                confidence=0.0,
                action_status="clarification_required",
                message="음성 transcript가 비어 있어 다시 말해달라고 요청합니다.",
                briefing="아직 들은 내용이 없습니다. 한 번 더 말해 주세요.",
                clarification_question="다시 한 번 짧게 말씀해 주세요.",
            )

        pending_action_id = runtime.voice_pending_action_id.strip()
        if pending_action_id:
            affirmatives = {"응", "예", "네", "확인", "좋아", "맞아", "진행해"}
            negatives = {"아니", "취소", "중단", "하지마", "그만"}
            if transcript in affirmatives or lowered in {token.lower() for token in affirmatives}:
                return build_result(
                    intent_id="confirm_yes",
                    confidence=0.98,
                    action_id=pending_action_id,
                    action_status="executed",
                    message=f"{pending_action_id} 확인을 받았습니다.",
                    briefing=f"확인했습니다. {pending_action_id} 동작을 이어가겠습니다.",
                )
            if transcript in negatives or lowered in {token.lower() for token in negatives}:
                return build_result(
                    intent_id="confirm_no",
                    confidence=0.98,
                    action_status="blocked",
                    message="대기 중이던 voice 확인 요청을 취소합니다.",
                    briefing="좋습니다. 대기 중이던 진행 요청은 취소하겠습니다.",
                )

        if any(token in transcript for token in ("왜 멈", "왜 보류", "멈춘 이유", "보류 이유")):
            return build_result(
                intent_id="why_paused",
                confidence=0.96,
                action_status="executed",
                message="현재 보류 이유를 음성 브리핑으로 정리합니다.",
                briefing=self.build_voice_briefing(session, runtime, intent_id="why_paused"),
            )

        if any(token in transcript for token in ("마지막 판단", "판단 읽", "판단 알려")):
            return build_result(
                intent_id="read_last_judgment",
                confidence=0.95,
                action_status="executed",
                message="마지막 판단 결과를 읽어줍니다.",
                briefing=self.build_voice_briefing(session, runtime, intent_id="read_last_judgment"),
            )

        if any(token in transcript for token in ("화면 모순", "마지막 화면", "마지막 시각", "visual")):
            return build_result(
                intent_id="read_last_visual",
                confidence=0.95,
                action_status="executed",
                message="마지막 시각 감독 결과를 읽어줍니다.",
                briefing=self.build_voice_briefing(session, runtime, intent_id="read_last_visual"),
            )

        if any(token in transcript for token in ("설정 열", "설정 보여", "control center", "설정 창")):
            return build_result(
                intent_id="open_settings",
                confidence=0.92,
                action_id="open_settings",
                action_status="executed",
                message="Control Center를 열겠습니다.",
                briefing=self.build_voice_briefing(session, runtime, intent_id="open_settings"),
            )

        if any(token in transcript for token in ("다시 읽", "다시 말", "한번 더", "한 번 더")):
            return build_result(
                intent_id="repeat_briefing",
                confidence=0.9,
                action_status="executed",
                message="마지막 브리핑을 다시 읽어줍니다.",
                briefing=self.build_voice_briefing(session, runtime, intent_id="repeat_briefing"),
            )

        if any(token in transcript for token in ("멈춰", "보류", "중지", "잠깐 멈춰", "그만")):
            return build_result(
                intent_id="pause_run",
                confidence=0.94,
                action_id="pause_auto",
                action_status="executed",
                message="현재 진행을 보류하겠습니다.",
                briefing=self.build_voice_briefing(session, runtime, intent_id="pause_run"),
            )

        if any(token in transcript for token in ("다음 단계", "계속 진행", "진행해", "계속해", "다음으로", "이어가")):
            if surface.state_key in {"setup_required", "target_required", "completed"}:
                return build_result(
                    intent_id="continue_step",
                    confidence=0.9,
                    action_status="blocked",
                    message="지금은 바로 continue할 수 있는 상태가 아닙니다.",
                    briefing=self.build_voice_briefing(session, runtime, intent_id="status_summary"),
                )

            high_risk_continue = (
                session.voice.confirmation_enabled
                and (
                    runtime.operator_paused
                    or runtime.last_judgment.decision == "ask_user"
                    or runtime.last_judgment.risk_level == "high"
                    or runtime.last_visual_result.contradiction_level == "high"
                )
            )
            if high_risk_continue:
                return build_result(
                    intent_id="continue_step",
                    confidence=0.91,
                    action_id="continue",
                    action_status="confirmation_required",
                    message="위험 신호가 있어 계속 진행 전 한 번 더 확인이 필요합니다.",
                    briefing="위험 신호가 있어 바로 진행하지 않겠습니다. 계속 진행하려면 한 번 더 확인해 주세요.",
                    requires_confirmation=True,
                )

            return build_result(
                intent_id="continue_step",
                confidence=0.93,
                action_id="continue",
                action_status="executed",
                message="다음 단계 진행 요청으로 이해했습니다.",
                briefing=self.build_voice_briefing(session, runtime, intent_id="continue_step"),
            )

        if any(token in transcript for token in ("상태 요약", "요약해", "브리핑", "지금 상태", "상태 읽어")):
            return build_result(
                intent_id="status_summary",
                confidence=0.9,
                action_status="executed",
                message="현재 상태 요약을 읽어줍니다.",
                briefing=self.build_voice_briefing(session, runtime, intent_id="status_summary"),
            )

        return build_result(
            intent_id="clarify",
            confidence=0.32,
            action_status="clarification_required",
            message="voice intent를 명확히 정하지 못했습니다.",
            briefing="명령을 정확히 이해하지 못했습니다. 진행, 보류, 상태 요약 중 하나로 다시 말해 주세요.",
            clarification_question="예: 다음 단계 진행해, 멈춰, 지금 상태 요약해줘",
        )

    def run_voice_command(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        transcript_text: str,
    ) -> VoiceCommandResult:
        result = self.interpret_voice_command(session, runtime, transcript_text)

        if result.action_status == "confirmation_required" and result.action_id:
            runtime.set_voice_pending_confirmation(result.action_id, result.message_to_user)
        elif result.normalized_intent_id in {"confirm_yes", "confirm_no"}:
            runtime.clear_voice_pending_confirmation()
        elif result.action_status != "confirmation_required":
            runtime.clear_voice_pending_confirmation()

        runtime.remember_voice_result(result, max_history_items=session.judgment.max_history_items)
        return result

    def build_judgment_packet(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        recent_log_lines: list[str] | None = None,
        visual_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        preview = self.build_prompt_preview(session, runtime)
        steps = session.project.steps()
        decision = self.recommend_codex_automation_mode(session, runtime)
        current_step = preview.step_title or "다음 단계 없음"
        recent_logs = [line.strip() for line in (recent_log_lines or []) if line.strip()]
        capture_name = Path(runtime.last_capture_path).name if runtime.last_capture_path else ""

        return {
            "cycle_context": {
                "evaluated_at": datetime.now().isoformat(timespec="seconds"),
                "current_step_index": preview.step_index,
                "current_step_title": current_step,
                "total_steps": len(steps),
                "auto_running": runtime.auto_running,
                "operator_paused": runtime.operator_paused,
                "operator_pause_reason": runtime.operator_pause_reason,
            },
            "project_context": {
                "project_summary": session.project.project_summary.strip(),
                "target_outcome": session.project.target_outcome.strip(),
                "steps": steps,
            },
            "runtime_context": {
                "stable_cycles": runtime.stable_cycles,
                "last_target_title": runtime.last_target_title,
                "last_target_reason": runtime.last_target_reason,
                "last_target_score": runtime.last_target_score,
                "target_lock_status": runtime.target_lock_status,
                "last_capture_name": capture_name,
                "last_capture_path": runtime.last_capture_path or "",
                "prompt_preview": {
                    "step_index": preview.step_index,
                    "step_title": preview.step_title,
                    "generated_prompt": preview.generated_prompt,
                    "draft_prompt": preview.draft_prompt,
                    "is_dirty": preview.is_dirty,
                    "is_complete": preview.is_complete,
                },
            },
            "policy_context": {
                "master_policy": session.policy.master_policy.strip(),
                "progress_policy": session.policy.progress_policy.strip(),
                "vision_policy": session.policy.vision_policy.strip(),
                "repair_policy": session.policy.repair_policy.strip(),
                "report_policy": session.policy.report_policy.strip(),
                "safety_policy": session.policy.safety_policy.strip(),
            },
            "evidence_context": {
                "recent_log_lines": recent_logs[-12:],
                "last_judgment": runtime.last_judgment.to_dict() if runtime.last_judgment.has_result else {},
                "last_visual_result": runtime.last_visual_result.to_dict() if runtime.last_visual_result.has_result else {},
                "visual_evidence": visual_context or {},
            },
            "automation_context": {
                "recommended_mode": decision.recommended_mode_id,
                "effective_mode": decision.effective_mode_id,
                "result_location": decision.result_location,
                "waiting_for": decision.waiting_for,
                "next_follow_up": decision.next_follow_up,
            },
            "user_override_context": {
                "codex_strategy_note": session.codex_strategy.custom_instruction.strip(),
            },
            "attachments": [
                {"type": "capture", "path": runtime.last_capture_path}
                for _ in [runtime.last_capture_path]
                if runtime.last_capture_path
            ],
        }

    def serialize_judgment_packet(self, packet: dict[str, Any]) -> str:
        return json.dumps(packet, ensure_ascii=False, indent=2)

    def build_judgment_prompt(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        *,
        packet: dict[str, Any] | None = None,
    ) -> str:
        active_packet = packet if packet is not None else self.build_judgment_packet(session, runtime)
        packet_text = self.serialize_judgment_packet(active_packet)
        threshold = session.judgment.confidence_threshold
        visual_note = ""
        if active_packet.get("evidence_context", {}).get("visual_evidence"):
            visual_note = "- visual evidence가 포함되어 있으므로 Codex 주장과 실제 화면의 모순을 더 강하게 반영합니다."
        return "\n".join(
            [
                "당신은 javis의 운영 판단 엔진입니다.",
                "현재 프로젝트와 최근 상태를 읽고 지금 무엇을 해야 하는지 안전하게 판단해 주세요.",
                "",
                "[판단 원칙]",
                session.policy.master_policy.strip() or "- 운영 마스터 미입력",
                "",
                "[단계 진행 정책]",
                session.policy.progress_policy.strip() or "- 단계 진행 정책 미입력",
                "",
                "[보정 지시 정책]",
                session.policy.repair_policy.strip() or "- 보정 지시 정책 미입력",
                "",
                "[사용자 보고 정책]",
                session.policy.report_policy.strip() or "- 사용자 보고 정책 미입력",
                "",
                "[안전 정책]",
                session.policy.safety_policy.strip() or "- 안전 정책 미입력",
                "",
                "[출력 계약]",
                "- 반드시 JSON 객체 하나만 반환합니다.",
                '- decision은 continue / wait / retry / pause / ask_user 중 하나여야 합니다.',
                "- reason, confidence, risk_level, message_to_user는 반드시 포함합니다.",
                "- risk_level은 low / medium / high 중 하나여야 합니다.",
                "- retry를 선택하면 next_prompt_to_codex를 반드시 포함합니다.",
                f"- continue confidence가 {threshold:.2f} 미만이면 계속 밀지 말고 pause 또는 ask_user 쪽을 우선합니다.",
                visual_note,
                "",
                "[반환 예시]",
                "{",
                '  "decision": "pause",',
                '  "reason": "근거가 부족해 자동 진행보다 보류가 안전합니다.",',
                '  "confidence": 0.72,',
                '  "risk_level": "medium",',
                '  "message_to_user": "근거가 부족해 잠시 멈추고 확인하는 편이 안전합니다.",',
                '  "needs_user_confirmation": false,',
                '  "next_prompt_to_codex": null,',
                '  "evidence_summary": ["최근 로그에 명확한 성공 신호가 없습니다."],',
                '  "follow_up_actions": ["재판단 실행", "최근 로그 확인"]',
                "}",
                "",
                "[판단 입력]",
                packet_text,
            ]
        ).strip()

    def build_retry_prompt(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        recent_log_lines: list[str] | None = None,
    ) -> str:
        preview = self.build_prompt_preview(session, runtime)
        step_label = preview.step_title or "현재 단계"
        error_lines = [line.strip() for line in (recent_log_lines or []) if line.strip()]
        evidence_lines = error_lines[-5:] if error_lines else ["- 최근 로그에서 명확한 성공 신호를 확인하지 못했습니다."]
        evidence_text = "\n".join(f"- {line}" for line in evidence_lines)
        return "\n".join(
            [
                "방금 단계 결과에서 보정이 필요해 보입니다. 같은 단계를 더 작고 안전한 범위로 다시 진행해 주세요.",
                "",
                f"현재 단계: {step_label}",
                "",
                "[보정 기준]",
                session.policy.repair_policy.strip() or "- 보정 지시 정책 미입력",
                "",
                "[안전 기준]",
                session.policy.safety_policy.strip() or "- 안전 정책 미입력",
                "",
                "[최근 근거]",
                evidence_text,
                "",
                "[요청]",
                "- 현재 단계만 다시 검토합니다.",
                "- 실패 원인 후보를 짧게 짚고, 한 번에 안정적으로 끝낼 수 있는 수정만 제안하거나 적용합니다.",
                "- 결과가 여전히 애매하면 다음 단계로 넘기지 말고 보류 또는 ask_user로 멈춥니다.",
            ]
        ).strip()

    def validate_judgment_response(
        self,
        response: JudgmentResult | dict[str, Any] | str,
        *,
        session: SessionConfig | None = None,
    ) -> JudgmentResult:
        raw_text = ""
        if isinstance(response, JudgmentResult):
            result = JudgmentResult.from_dict(response.to_dict())
        elif isinstance(response, dict):
            result = JudgmentResult.from_dict(response)
        elif isinstance(response, str):
            raw_text = response.strip()
            try:
                result = JudgmentResult.from_dict(json.loads(raw_text))
            except json.JSONDecodeError:
                result = JudgmentResult(
                    decision="pause",
                    reason="판단 응답이 JSON 계약을 지키지 않아 안전하게 보류했습니다.",
                    confidence=0.0,
                    risk_level="medium",
                    message_to_user="판단 응답 형식이 올바르지 않아 잠시 멈췄습니다.",
                    needs_user_confirmation=False,
                    source="validator",
                    validation_notes=["JSON 파싱 실패로 pause 처리했습니다."],
                    evaluated_at=datetime.now().isoformat(timespec="seconds"),
                    raw_response=raw_text,
                )
                return result
        else:
            result = JudgmentResult()

        if raw_text and not result.raw_response:
            result.raw_response = raw_text
        if not result.evaluated_at:
            result.evaluated_at = datetime.now().isoformat(timespec="seconds")

        notes = list(result.validation_notes)
        allowed_decisions = {"continue", "wait", "retry", "pause", "ask_user"}
        allowed_risks = {"low", "medium", "high"}
        threshold = session.judgment.confidence_threshold if session is not None else 0.6

        if result.decision not in allowed_decisions:
            notes.append("알 수 없는 decision이라 pause로 강등했습니다.")
            result.decision = "pause"
            result.reason = result.reason or "판단 응답의 decision 값이 계약과 달라 보류했습니다."
            result.message_to_user = result.message_to_user or "판단 형식이 맞지 않아 잠시 멈췄습니다."

        if result.risk_level not in allowed_risks:
            notes.append("risk_level이 계약과 달라 medium으로 보정했습니다.")
            result.risk_level = "medium"

        result.confidence = min(max(float(result.confidence or 0.0), 0.0), 1.0)
        if not result.reason.strip():
            notes.append("reason이 비어 있어 pause로 강등했습니다.")
            result.decision = "pause"
            result.reason = "판단 이유가 비어 있어 자동 집행보다 보류가 안전합니다."
        if not result.message_to_user.strip():
            result.message_to_user = result.reason

        if result.decision == "retry" and not (result.next_prompt_to_codex or "").strip():
            notes.append("retry인데 next_prompt_to_codex가 없어 pause로 강등했습니다.")
            result.decision = "pause"
            result.reason = "재시도 프롬프트가 없어 자동 retry 대신 보류했습니다."
            result.message_to_user = "재지시 문구가 없어 잠시 멈추고 확인이 필요합니다."

        if result.decision == "continue" and result.risk_level == "high":
            notes.append("high risk continue를 ask_user로 강등했습니다.")
            result.decision = "ask_user"
            result.needs_user_confirmation = True
            result.reason = "위험도가 높은 상태라 자동 continue 대신 사람 확인이 필요합니다."
            result.message_to_user = "위험도가 높아 바로 진행하지 않고 확인이 필요합니다."

        if result.decision == "continue" and result.confidence < threshold:
            notes.append("confidence가 threshold보다 낮아 pause로 강등했습니다.")
            result.decision = "pause"
            result.reason = "확신이 충분하지 않아 자동 continue 대신 보류했습니다."
            result.message_to_user = "확신이 낮아 잠시 멈추고 다시 확인하는 편이 안전합니다."

        result.validation_notes = notes
        return result

    def run_rule_based_judgment(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        *,
        packet: dict[str, Any] | None = None,
        recent_log_lines: list[str] | None = None,
    ) -> JudgmentResult:
        active_packet = packet if packet is not None else self.build_judgment_packet(session, runtime, recent_log_lines)
        preview = self.build_prompt_preview(session, runtime)
        steps = session.project.steps()
        log_lines = [line.strip() for line in (recent_log_lines or []) if line.strip()]
        lowered = "\n".join(log_lines).lower()
        source = "rule_based"
        if session.judgment.engine_mode_id == "auto":
            source = "auto_fallback"
        visual_evidence = active_packet.get("evidence_context", {}).get("visual_evidence", {})
        visual_result = visual_evidence.get("result", {}) if isinstance(visual_evidence, dict) else {}
        if visual_result:
            source = "visual_rejudge"

        evidence_summary = [
            f"운영 mode: {active_packet['automation_context']['effective_mode']}",
            f"타깃 상태: {runtime.last_target_reason or '없음'}",
        ]
        if runtime.last_capture_path:
            evidence_summary.append(f"최근 캡처: {Path(runtime.last_capture_path).name}")
        if log_lines:
            evidence_summary.append(f"최근 로그 {min(len(log_lines), 3)}줄을 참고했습니다.")
        if visual_result:
            evidence_summary.append(
                f"시각 판단: {visual_result.get('target_label', '화면')} | contradiction {visual_result.get('contradiction_level', 'none')}"
            )
            mismatch_signals = visual_result.get("mismatch_signals", []) or []
            if mismatch_signals:
                evidence_summary.append(f"시각 mismatch: {', '.join(mismatch_signals)}")

        if visual_result.get("contradiction_detected"):
            contradiction_level = visual_result.get("contradiction_level", "medium")
            if contradiction_level == "high":
                return JudgmentResult(
                    decision="ask_user",
                    reason=visual_result.get(
                        "contradiction_reason",
                        "시각 증거에서 큰 모순 신호가 보여 상단장님 확인이 우선입니다.",
                    ),
                    confidence=0.95,
                    risk_level="high",
                    message_to_user=visual_result.get(
                        "message_to_user",
                        "화면 근거에서 큰 모순이 보여 바로 진행하지 않고 확인이 필요합니다.",
                    ),
                    needs_user_confirmation=True,
                    evidence_summary=evidence_summary,
                    follow_up_actions=["시각 근거 확인", "상단장님 확인", "필요 시 재지시"],
                    source=source,
                    evaluated_at=datetime.now().isoformat(timespec="seconds"),
                )
            return JudgmentResult(
                decision="retry",
                reason=visual_result.get(
                    "contradiction_reason",
                    "시각 증거에서 현재 단계와 어긋나는 신호가 보여 같은 단계를 보정해 다시 시도하는 편이 안전합니다.",
                ),
                confidence=0.88,
                risk_level="medium",
                message_to_user=visual_result.get(
                    "message_to_user",
                    "화면 모순이 보여 같은 단계를 보정해서 다시 시도하는 편이 좋습니다.",
                ),
                next_prompt_to_codex=self.build_retry_prompt(session, runtime, log_lines),
                evidence_summary=evidence_summary,
                follow_up_actions=["보정 프롬프트 검토", "시각 근거 확인", "같은 단계 재지시"],
                source=source,
                evaluated_at=datetime.now().isoformat(timespec="seconds"),
            )

        high_risk_keywords = (
            "삭제",
            "remove-item",
            "drop table",
            "billing",
            "과금",
            "production",
            "배포",
            "deploy",
            "권한",
            "permission",
        )
        retry_keywords = (
            "error",
            "failed",
            "failure",
            "traceback",
            "exception",
            "오류",
            "에러",
            "실패",
            "빌드 실패",
            "test failed",
        )

        if any(keyword in lowered for keyword in high_risk_keywords):
            return JudgmentResult(
                decision="ask_user",
                reason="되돌리기 어렵거나 운영상 위험한 신호가 보여 자동 진행보다 사람 확인이 우선입니다.",
                confidence=0.92,
                risk_level="high",
                message_to_user="위험 신호가 보여 바로 진행하지 않고 상단장님 확인이 필요합니다.",
                needs_user_confirmation=True,
                evidence_summary=evidence_summary + ["최근 로그에서 위험 키워드를 감지했습니다."],
                follow_up_actions=["로그 확인", "필요 시 수동 승인 후 진행"],
                source=source,
                evaluated_at=datetime.now().isoformat(timespec="seconds"),
            )

        if not steps:
            return JudgmentResult(
                decision="pause",
                reason="프로젝트 단계가 비어 있어 무엇을 진행할지 먼저 정리해야 합니다.",
                confidence=0.98,
                risk_level="low",
                message_to_user="단계 목록이 아직 없어 먼저 계획을 채워야 합니다.",
                evidence_summary=evidence_summary + ["단계 목록이 비어 있습니다."],
                follow_up_actions=["프로젝트 / 단계 입력", "다시 재판단"],
                source=source,
                evaluated_at=datetime.now().isoformat(timespec="seconds"),
            )

        if runtime.next_step_index >= len(steps) or preview.is_complete:
            return JudgmentResult(
                decision="ask_user",
                reason="현재 등록된 단계는 모두 전송되어 결과 검토나 다음 계획 결정이 필요한 시점입니다.",
                confidence=0.94,
                risk_level="low",
                message_to_user="현재 단계 묶음은 끝났습니다. 결과 확인이나 다음 계획이 필요합니다.",
                needs_user_confirmation=True,
                evidence_summary=evidence_summary + ["등록된 단계가 모두 소진되었습니다."],
                follow_up_actions=["결과 검토", "다음 단계 추가"],
                source=source,
                evaluated_at=datetime.now().isoformat(timespec="seconds"),
            )

        if runtime.operator_paused:
            return JudgmentResult(
                decision="pause",
                reason=runtime.operator_pause_reason or "운영자 보류 상태라 재개 전까지 멈추는 편이 안전합니다.",
                confidence=0.95,
                risk_level="medium",
                message_to_user="현재 보류 상태라 재개 전까지 멈춰 둡니다.",
                evidence_summary=evidence_summary + ["operator_paused가 켜져 있습니다."],
                follow_up_actions=["재개 여부 확인", "필요 시 재판단"],
                source=source,
                evaluated_at=datetime.now().isoformat(timespec="seconds"),
            )

        if not runtime.last_target_title:
            return JudgmentResult(
                decision="pause",
                reason="Codex 창이 아직 확정되지 않아 진행보다 대상 안정화가 먼저입니다.",
                confidence=0.96,
                risk_level="medium",
                message_to_user="Codex 창을 먼저 찾고 포커스한 뒤 다시 판단하는 편이 안전합니다.",
                evidence_summary=evidence_summary + ["타깃 창이 아직 비어 있습니다."],
                follow_up_actions=["창 찾기", "Codex 포커스", "재판단"],
                source=source,
                evaluated_at=datetime.now().isoformat(timespec="seconds"),
            )

        if any(keyword in lowered for keyword in retry_keywords):
            return JudgmentResult(
                decision="retry",
                reason="최근 로그와 상태에서 오류 또는 실패 신호가 보여 현재 단계를 보정 프롬프트로 다시 시도하는 편이 안전합니다.",
                confidence=0.79,
                risk_level="medium",
                message_to_user="오류 신호가 보여 같은 단계를 보정 프롬프트로 다시 시도하는 편이 좋습니다.",
                next_prompt_to_codex=self.build_retry_prompt(session, runtime, log_lines),
                evidence_summary=evidence_summary + ["최근 로그에서 오류/실패 키워드를 감지했습니다."],
                follow_up_actions=["보정 프롬프트 검토", "같은 단계 재지시"],
                source=source,
                evaluated_at=datetime.now().isoformat(timespec="seconds"),
            )

        if runtime.auto_running and runtime.stable_cycles < session.automation.stable_cycles_required:
            return JudgmentResult(
                decision="wait",
                reason="자동 감시 중이며 안정화 카운트가 아직 기준에 못 미쳐 조금 더 관찰하는 편이 좋습니다.",
                confidence=0.76,
                risk_level="low",
                message_to_user="아직 화면이 충분히 안정되지 않아 조금 더 지켜보는 편이 좋습니다.",
                evidence_summary=evidence_summary + ["자동 감시가 진행 중이고 안정화 카운트가 충분하지 않습니다."],
                follow_up_actions=["자동 감시 유지", "필요 시 재판단"],
                source=source,
                evaluated_at=datetime.now().isoformat(timespec="seconds"),
            )

        dry_run_reason = (
            "현재는 DRY RUN이라 실제 전송 전에 판단 결과만 먼저 점검하는 상태입니다."
            if session.automation.dry_run
            else "현재 단계 프롬프트와 타깃 창 상태가 모두 준비되어 다음 단계로 이어갈 수 있습니다."
        )
        dry_run_message = (
            "DRY RUN 기준으로는 계속 진행 가능해 보입니다. 실제 전송 전 한 번 더 확인하면 됩니다."
            if session.automation.dry_run
            else "지금 상태라면 다음 단계로 이어가도 됩니다."
        )
        follow_up = ["현재 프롬프트 확인", "다음 단계 진행"]
        if session.automation.dry_run:
            follow_up.insert(0, "DRY RUN 결과 검토")
        return JudgmentResult(
            decision="continue",
            reason=dry_run_reason,
            confidence=0.81,
            risk_level="low",
            message_to_user=dry_run_message,
            next_prompt_to_codex=preview.draft_prompt,
            evidence_summary=evidence_summary + [f"현재 단계: {preview.step_title}"],
            follow_up_actions=follow_up,
            source=source,
            evaluated_at=datetime.now().isoformat(timespec="seconds"),
        )

    def format_judgment_result(self, result: JudgmentResult) -> str:
        return json.dumps(
            {
                "decision": result.decision,
                "reason": result.reason,
                "confidence": round(result.confidence, 3),
                "risk_level": result.risk_level,
                "message_to_user": result.message_to_user,
                "needs_user_confirmation": result.needs_user_confirmation,
                "next_prompt_to_codex": result.next_prompt_to_codex,
                "evidence_summary": result.evidence_summary,
                "follow_up_actions": result.follow_up_actions,
                "source": result.source,
                "validation_notes": result.validation_notes,
                "evaluated_at": result.evaluated_at,
            },
            ensure_ascii=False,
            indent=2,
        )

    def run_judgment(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        *,
        recent_log_lines: list[str] | None = None,
        visual_context: dict[str, Any] | None = None,
    ) -> JudgmentResult:
        packet = self.build_judgment_packet(session, runtime, recent_log_lines, visual_context=visual_context)
        prompt = self.build_judgment_prompt(session, runtime, packet=packet)
        result = self.run_rule_based_judgment(
            session,
            runtime,
            packet=packet,
            recent_log_lines=recent_log_lines,
        )
        validated = self.validate_judgment_response(result, session=session)
        if session.judgment.engine_mode_id == "auto":
            validated.validation_notes.append("OpenAI 연결 전이라 현재는 규칙 기반 fallback으로 판단했습니다.")
        response_text = self.format_judgment_result(validated)
        runtime.remember_judgment(
            validated,
            packet_text=self.serialize_judgment_packet(packet),
            prompt_text=prompt,
            response_text=response_text,
            max_history_items=session.judgment.max_history_items,
        )
        return validated

    def build_judgment_timeline(self, runtime: RuntimeState) -> str:
        lines = ["[Judgment Timeline]"]
        if runtime.last_judgment.has_result:
            result = runtime.last_judgment
            lines.extend(
                [
                    f"최근 판단: {result.decision} | conf {result.confidence:.2f} | risk {result.risk_level}",
                    f"판단 이유: {result.reason}",
                    f"사용자 요약: {result.message_to_user}",
                    f"소스: {result.source or 'unknown'}",
                ]
            )
            if result.evidence_summary:
                lines.extend(["", "[근거 요약]"])
                lines.extend(f"- {item}" for item in result.evidence_summary)
            if result.follow_up_actions:
                lines.extend(["", "[후속 행동]"])
                lines.extend(f"- {item}" for item in result.follow_up_actions)
            if result.validation_notes:
                lines.extend(["", "[검증 메모]"])
                lines.extend(f"- {item}" for item in result.validation_notes)
        else:
            lines.append("아직 저장된 판단 결과가 없습니다.")

        lines.extend(["", "[최근 판단 이력]"])
        if runtime.judgment_history:
            lines.extend(f"- {item.display_line()}" for item in runtime.judgment_history)
        else:
            lines.append("- 판단 이력이 아직 없습니다.")
        return "\n".join(lines).strip()

    def apply_judgment_surface_overlay(
        self,
        base_state: SurfaceStateModel,
        session: SessionConfig,
        runtime: RuntimeState,
        *,
        preview: PromptPreview | None = None,
    ) -> SurfaceStateModel:
        result = runtime.last_judgment
        if not result.has_result:
            return base_state

        risk_label = {"low": "낮음", "medium": "보통", "high": "높음"}.get(result.risk_level, result.risk_level)
        detail_label = f"판단 {result.decision} | conf {result.confidence:.2f} | source {result.source or 'unknown'}"
        next_action = result.follow_up_actions[0] if result.follow_up_actions else result.message_to_user or base_state.next_action

        if result.decision == "retry":
            return SurfaceStateModel(
                state_key="judgment_retry",
                project_label=base_state.project_label,
                badge_label="보정",
                title="재지시 권장",
                summary=result.message_to_user or "현재 단계는 보정 프롬프트로 다시 시도하는 편이 좋습니다.",
                reason=result.reason,
                next_action=next_action,
                progress_label=base_state.progress_label,
                detail_label=detail_label,
                risk_label=risk_label,
                actions=[
                    PopupActionModel("retry_now", "재지시", True, "primary"),
                    PopupActionModel("rejudge", "재판단", True),
                    PopupActionModel("show_summary", "요약", True),
                    PopupActionModel("open_settings", "설정", True),
                ],
            )

        if result.decision == "wait":
            primary_action = PopupActionModel("start_auto", "감시", True, "primary")
            if runtime.auto_running:
                primary_action = PopupActionModel("pause_auto", "멈춤", True, "primary")
            return SurfaceStateModel(
                state_key="judgment_wait",
                project_label=base_state.project_label,
                badge_label="관찰",
                title="조금 더 지켜보는 편이 좋습니다.",
                summary=result.message_to_user or "지금은 바로 밀기보다 조금 더 관찰하는 편이 안전합니다.",
                reason=result.reason,
                next_action=next_action,
                progress_label=base_state.progress_label,
                detail_label=detail_label,
                risk_label=risk_label,
                actions=[
                    primary_action,
                    PopupActionModel("rejudge", "재판단", True),
                    PopupActionModel("show_summary", "요약", True),
                    PopupActionModel("open_settings", "설정", True),
                ],
            )

        if result.decision in {"pause", "ask_user"}:
            return SurfaceStateModel(
                state_key="judgment_pause",
                project_label=base_state.project_label,
                badge_label="확인 필요" if result.decision == "ask_user" else "보류",
                title="바로 진행보다 확인이 우선입니다.",
                summary=result.message_to_user or "지금은 멈추고 확인하는 편이 안전합니다.",
                reason=result.reason,
                next_action=next_action,
                progress_label=base_state.progress_label,
                detail_label=detail_label,
                risk_label=risk_label,
                actions=[
                    PopupActionModel("rejudge", "재판단", True, "primary"),
                    PopupActionModel("show_summary", "요약", True),
                    PopupActionModel("open_settings", "설정", True),
                    PopupActionModel("capture_now", "캡처", True),
                ],
            )

        if result.decision == "continue":
            return SurfaceStateModel(
                state_key="judgment_continue",
                project_label=base_state.project_label,
                badge_label="진행 가능",
                title="계속 진행해도 됩니다.",
                summary=result.message_to_user or base_state.summary,
                reason=result.reason,
                next_action=next_action,
                progress_label=base_state.progress_label,
                detail_label=detail_label,
                risk_label=risk_label,
                actions=[
                    PopupActionModel("continue", "진행", True, "primary"),
                    PopupActionModel("rejudge", "재판단", True),
                    PopupActionModel("show_summary", "요약", True),
                    PopupActionModel("open_settings", "설정", True),
                ],
            )

        return base_state

    def build_surface_state(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
        preview: PromptPreview | None = None,
        queue: list[StepQueueItem] | None = None,
    ) -> SurfaceStateModel:
        active_queue = queue if queue is not None else self.build_step_queue(session, runtime)
        active_preview = preview if preview is not None else self.build_prompt_preview(session, runtime)

        total_steps = len(active_queue)
        completed_steps = min(runtime.next_step_index, total_steps)
        score_text = "없음" if runtime.last_target_score is None else str(runtime.last_target_score)
        capture_name = Path(runtime.last_capture_path).name if runtime.last_capture_path else "없음"
        project_label = (
            session.project.project_summary
            or session.project.target_outcome
            or "프로젝트 정보 미입력"
        )
        progress_label = f"진행 {completed_steps}/{total_steps}"
        detail_label = (
            f"타깃 점수 {score_text} | 안정 카운트 {runtime.stable_cycles} | 최근 캡처 {capture_name}"
        )

        current_step_title = active_preview.step_title or "다음 단계"

        if total_steps == 0:
            return SurfaceStateModel(
                state_key="setup_required",
                project_label=project_label,
                badge_label="준비",
                title="프로젝트 설정 대기",
                summary="단계 목록과 프로젝트 설명이 아직 준비되지 않았습니다.",
                reason="팝업은 핵심 상태만 보여주기 때문에 먼저 프로젝트 입력이 끝나야 제대로 안내할 수 있습니다.",
                next_action="설정을 열어 프로젝트 요약, 목표, 단계 목록을 먼저 채워 주세요.",
                progress_label=progress_label,
                detail_label=detail_label,
                risk_label="낮음",
                actions=[
                    PopupActionModel("open_settings", "설정", True, "primary"),
                    PopupActionModel("show_summary", "요약", True),
                    PopupActionModel("refresh_windows", "창 확인", True),
                    PopupActionModel("continue", "진행", False),
                ],
            )

        if active_preview.is_complete or runtime.next_step_index >= total_steps:
            return SurfaceStateModel(
                state_key="completed",
                project_label=project_label,
                badge_label="완료",
                title="현재 계획 전송 완료",
                summary="등록된 모든 단계를 Codex에 전송한 상태입니다.",
                reason="이제 결과 검토, 추가 플랜 입력, 또는 다음 릴리즈 작업으로 넘어갈 시점입니다.",
                next_action="결과를 검토한 뒤 계획을 갱신하거나 캡처를 남겨 다음 판단 입력으로 넘기면 됩니다.",
                progress_label=progress_label,
                detail_label=detail_label,
                risk_label="낮음",
                actions=[
                    PopupActionModel("open_settings", "계획 갱신", True, "primary"),
                    PopupActionModel("show_summary", "요약", True),
                    PopupActionModel("capture_now", "캡처", True),
                    PopupActionModel("refresh_windows", "창 확인", True),
                ],
            )

        if runtime.operator_paused:
            primary_action = (
                PopupActionModel("resume_ready", "재개", True, "primary")
                if runtime.last_target_title
                else PopupActionModel("refresh_windows", "창 찾기", True, "primary")
            )
            secondary_action = (
                PopupActionModel("capture_now", "캡처", True)
                if runtime.last_target_title
                else PopupActionModel("focus_codex", "포커스", True)
            )
            return SurfaceStateModel(
                state_key="paused",
                project_label=project_label,
                badge_label="보류",
                title="운영자 확인 대기",
                summary="javis가 현재 진행을 잠시 보류한 상태입니다.",
                reason=runtime.operator_pause_reason or runtime.last_target_reason or "명시적인 재개 요청 전까지 다음 단계를 멈춰 둡니다.",
                next_action="재개로 다시 이어가거나 설정에서 프롬프트와 대상을 점검해 주세요.",
                progress_label=progress_label,
                detail_label=detail_label,
                risk_label="주의",
                actions=[
                    primary_action,
                    PopupActionModel("voice_brief", "브리핑", True),
                    PopupActionModel("open_settings", "설정", True),
                    secondary_action,
                ],
            )

        if not runtime.last_target_title:
            return SurfaceStateModel(
                state_key="target_required",
                project_label=project_label,
                badge_label="대기",
                title="Codex 창 확인 필요",
                summary="아직 제어할 Codex 창을 확정하지 못했습니다.",
                reason=runtime.last_target_reason or "이전 성공 창이 없거나 현재 창 조건이 맞지 않습니다.",
                next_action="창 찾기나 포커스로 Codex 대상을 먼저 안정화해 주세요.",
                progress_label=progress_label,
                detail_label=detail_label,
                risk_label="주의",
                actions=[
                    PopupActionModel("refresh_windows", "창 찾기", True, "primary"),
                    PopupActionModel("focus_codex", "포커스", True),
                    PopupActionModel("show_summary", "요약", True),
                    PopupActionModel("open_settings", "설정", True),
                ],
            )

        if runtime.auto_running:
            return SurfaceStateModel(
                state_key="monitoring",
                project_label=project_label,
                badge_label="관찰 중",
                title="자동 루프 실행 중",
                summary="Codex 화면이 안정될 때까지 계속 관찰하고 있습니다.",
                reason=runtime.last_target_reason or "다음 전송 시점이 올 때까지 자동으로 상태를 보고 있습니다.",
                next_action="필요하면 멈춤으로 자동 루프를 중지하고, 아니면 javis가 계속 감시하게 두면 됩니다.",
                progress_label=progress_label,
                detail_label=detail_label,
                risk_label="낮음" if session.automation.dry_run else "보통",
                actions=[
                    PopupActionModel("pause_auto", "멈춤", True, "primary"),
                    PopupActionModel("voice_brief", "브리핑", True),
                    PopupActionModel("capture_now", "캡처", True),
                    PopupActionModel("open_settings", "설정", True),
                ],
            )

        if session.automation.dry_run:
            return SurfaceStateModel(
                state_key="ready_dry_run",
                project_label=project_label,
                badge_label="검토",
                title="DRY RUN 진행 준비",
                summary=f"{current_step_title} 단계를 검토 모드로 보낼 준비가 되어 있습니다.",
                reason="현재는 실제 전송보다 프롬프트와 루프 흐름 검토를 우선하는 상태입니다.",
                next_action="진행으로 현재 프롬프트를 확인하거나 자동 감시를 켜서 루프를 시험해 보세요.",
                progress_label=progress_label,
                detail_label=detail_label,
                risk_label="낮음",
                actions=[
                    PopupActionModel("continue", "진행", True, "primary"),
                    PopupActionModel("pause_auto", "보류", True),
                    PopupActionModel("voice_brief", "브리핑", True),
                    PopupActionModel("open_settings", "설정", True),
                ],
            )

        return SurfaceStateModel(
            state_key="ready_live",
            project_label=project_label,
            badge_label="진행 가능",
            title="다음 단계 준비 완료",
            summary=f"{current_step_title} 단계를 보낼 준비가 되어 있습니다.",
            reason=runtime.last_target_reason or "타깃 창, 단계 큐, 입력 좌표가 모두 준비되어 있습니다.",
            next_action="진행으로 다음 단계를 보내거나 자동 감시를 켜서 javis가 계속 이어가게 할 수 있습니다.",
            progress_label=progress_label,
            detail_label=detail_label,
            risk_label="보통",
            actions=[
                PopupActionModel("continue", "진행", True, "primary"),
                PopupActionModel("pause_auto", "보류", True),
                PopupActionModel("voice_brief", "브리핑", True),
                PopupActionModel("open_settings", "설정", True),
            ],
        )

    def run_cycle(self, session: SessionConfig, runtime: RuntimeState) -> CycleReport:
        resolution = self.bridge.resolve_target(session.window)
        self._sync_runtime_target(runtime, resolution)
        preview = self.build_prompt_preview(session, runtime)
        if resolution.selected is None:
            runtime.reset_stability()
            return CycleReport(
                window_found=False,
                message=resolution.summary(),
                target_reason=resolution.reason_text,
                target_score=None,
                lock_status=resolution.lock_status,
                step_index=preview.step_index,
                step_title=preview.step_title,
            )

        target = resolution.selected
        capture_path = self.capture_dir / f"codex-{datetime.now().strftime('%Y%m%d-%H%M%S')}.bmp"
        self.bridge.capture_window(target.handle, capture_path)
        self._remember_target(session, resolution)

        signature = compute_signature(capture_path)
        distance = normalized_distance(runtime.last_signature, signature)
        if distance <= session.automation.signature_threshold:
            runtime.stable_cycles += 1
        else:
            runtime.stable_cycles = 0

        runtime.last_signature = signature
        runtime.last_capture_path = str(capture_path)

        report = CycleReport(
            window_found=True,
            window_title=target.title,
            capture_path=str(capture_path),
            stable_cycles=runtime.stable_cycles,
            signature_distance=distance,
            message=f"{resolution.summary()} 안정화 카운트 {runtime.stable_cycles}",
            target_reason=resolution.reason_text,
            target_score=resolution.score,
            lock_status=resolution.lock_status,
            step_index=preview.step_index,
            step_title=preview.step_title,
        )

        steps = session.project.steps()
        cooldown_elapsed = time.time() - runtime.last_action_at
        can_advance = (
            runtime.next_step_index < len(steps)
            and runtime.stable_cycles >= session.automation.stable_cycles_required
            and cooldown_elapsed >= session.automation.min_seconds_between_actions
        )
        if not can_advance:
            return report

        prompt = preview.draft_prompt
        prompt_source = "edited" if preview.is_dirty else "generated"
        if session.automation.dry_run:
            report.action_taken = True
            report.step_sent = prompt
            report.generated_prompt = preview.generated_prompt
            report.prompt_source = prompt_source
            report.message = (
                f"{resolution.summary()} 다음 단계 전송 조건을 만족했지만 "
                "현재는 DRY RUN이라 실제 전송은 하지 않았습니다."
            )
            runtime.last_action_at = time.time()
            runtime.stable_cycles = 0
            return report

        click_x, click_y = self._resolve_input_click(session, target.handle)
        self.bridge.send_text(
            target.handle,
            prompt,
            click_x=click_x,
            click_y=click_y,
            submit=session.automation.submit_with_enter,
        )
        runtime.last_action_at = time.time()
        runtime.next_step_index += 1
        runtime.stable_cycles = 0
        runtime.clear_prompt_preview()
        self._remember_target(session, resolution)
        report.action_taken = True
        report.step_sent = prompt
        report.generated_prompt = preview.generated_prompt
        report.prompt_source = prompt_source
        report.message = f"{resolution.summary()} 다음 단계 {runtime.next_step_index}개째를 Codex에 전송했습니다."
        return report

    def send_next_step_now(self, session: SessionConfig, runtime: RuntimeState) -> CycleReport:
        resolution = self.bridge.resolve_target(session.window)
        self._sync_runtime_target(runtime, resolution)
        preview = self.build_prompt_preview(session, runtime)
        if resolution.selected is None:
            return CycleReport(
                window_found=False,
                message=resolution.summary(),
                target_reason=resolution.reason_text,
                target_score=None,
                lock_status=resolution.lock_status,
                step_index=preview.step_index,
                step_title=preview.step_title,
            )

        target = resolution.selected
        steps = session.project.steps()
        if runtime.next_step_index >= len(steps):
            self._remember_target(session, resolution)
            return CycleReport(
                window_found=True,
                window_title=target.title,
                message=f"{resolution.summary()} 남은 단계가 없습니다.",
                target_reason=resolution.reason_text,
                target_score=resolution.score,
                lock_status=resolution.lock_status,
            )

        prompt = preview.draft_prompt
        prompt_source = "edited" if preview.is_dirty else "generated"
        if session.automation.dry_run:
            runtime.last_action_at = time.time()
            runtime.stable_cycles = 0
            return CycleReport(
                window_found=True,
                window_title=target.title,
                action_taken=True,
                step_sent=prompt,
                generated_prompt=preview.generated_prompt,
                prompt_source=prompt_source,
                step_index=preview.step_index,
                step_title=preview.step_title,
                message=f"{resolution.summary()} DRY RUN 상태라 실제 전송 없이 프롬프트만 생성했습니다.",
                target_reason=resolution.reason_text,
                target_score=resolution.score,
                lock_status=resolution.lock_status,
            )

        click_x, click_y = self._resolve_input_click(session, target.handle)
        self.bridge.send_text(
            target.handle,
            prompt,
            click_x=click_x,
            click_y=click_y,
            submit=session.automation.submit_with_enter,
        )
        self._remember_target(session, resolution)
        runtime.next_step_index += 1
        runtime.last_action_at = time.time()
        runtime.stable_cycles = 0
        runtime.clear_prompt_preview()
        return CycleReport(
            window_found=True,
            window_title=target.title,
            action_taken=True,
            step_sent=prompt,
            generated_prompt=preview.generated_prompt,
            prompt_source=prompt_source,
            step_index=preview.step_index,
            step_title=preview.step_title,
            message=f"{resolution.summary()} 다음 단계 {runtime.next_step_index}개째를 수동 전송했습니다.",
            target_reason=resolution.reason_text,
            target_score=resolution.score,
            lock_status=resolution.lock_status,
        )

    def build_step_prompt(self, session: SessionConfig, step_index: int) -> str:
        steps = session.project.steps()
        step = steps[step_index]
        total = len(steps)
        rules_text = session.policy.build_rules_for_prompt()
        return "\n".join(
            [
                "이전 단계가 끝났다면 다음 단계만 이어서 진행해 주세요.",
                "",
                f"프로젝트 요약: {session.project.project_summary or '미입력'}",
                f"목표 수준: {session.project.target_outcome or '미입력'}",
                f"현재 단계: {step_index + 1}/{total}",
                f"이번 단계: {step}",
                "",
                "운영 규칙:",
                rules_text,
            ]
        )

    def recommend_codex_automation_mode(
        self,
        session: SessionConfig,
        runtime: RuntimeState | None = None,
    ) -> CodexAutomationModeDecision:
        preset = get_codex_automation_preset(session.codex_strategy.selected_preset_id)
        steps = session.project.steps()
        preset_id = preset.preset_id
        automation_type = preset.automation_type.lower()

        if not steps:
            recommended_mode_id = "no_automation"
            recommended_reason = "단계 목록이 아직 비어 있어서, automation보다 현재 스레드에서 계획을 먼저 정리하는 편이 맞습니다."
        elif preset_id == "masterplan_followup":
            recommended_mode_id = "no_automation"
            recommended_reason = (
                "이 시나리오는 마스터플랜을 이미 세운 뒤 같은 스레드에서 순차 진행하는 흐름이 중심이라, "
                "지금은 automation 없이 이어가는 편이 더 단순합니다."
            )
        elif preset_id == "pr_babysit":
            recommended_mode_id = "thread_automation"
            recommended_reason = (
                "PR 대응은 같은 문맥에서 새 변화만 이어보는 흐름이 많아서, 같은 스레드를 깨우는 thread automation이 잘 맞습니다."
            )
        elif preset_id in {"release_smoke", "nightly_brief", "ci_failure_triage", "recent_code_bugfix"}:
            recommended_mode_id = "project_automation"
            recommended_reason = (
                "이 시나리오는 독립 실행 결과를 따로 받고 다시 triage하는 편이 자연스러워서 project automation이 잘 맞습니다."
            )
        elif "thread automation" in automation_type and "project automation" not in automation_type and "standalone" not in automation_type:
            recommended_mode_id = "thread_automation"
            recommended_reason = "선택한 프리셋이 같은 스레드 문맥 유지에 더 맞아서 thread automation을 추천합니다."
        elif "project automation" in automation_type or "standalone" in automation_type:
            recommended_mode_id = "project_automation"
            recommended_reason = "선택한 프리셋이 독립 실행 보고 흐름에 더 맞아서 project automation을 추천합니다."
        else:
            recommended_mode_id = "no_automation"
            recommended_reason = "지금 프로젝트는 먼저 같은 스레드 순차 진행으로도 충분히 운영 가능해 보여 no automation을 우선 추천합니다."

        selected_mode_id = session.codex_strategy.selected_mode_id or "recommended"
        effective_mode_id = recommended_mode_id if selected_mode_id == "recommended" else selected_mode_id

        recommended_option = get_codex_automation_mode_option(recommended_mode_id)
        effective_option = get_codex_automation_mode_option(effective_mode_id)
        if selected_mode_id == "recommended":
            effective_reason = f"현재는 추천값을 그대로 따릅니다. {recommended_reason}"
        elif effective_mode_id == recommended_mode_id:
            effective_reason = f"추천값과 같은 mode를 직접 고른 상태입니다. {recommended_reason}"
        else:
            effective_reason = (
                f"추천은 {recommended_option.title}이지만, 현재는 {effective_option.title}로 수동 고정했습니다. "
                "실전에서는 이 override가 정말 필요한지 한 번 더 확인하는 편이 좋습니다."
            )

        if effective_mode_id == "no_automation":
            cadence_hint = "cadence 없음 | 현재 스레드에서 결과가 오면 바로 이어서 진행"
            worktree_hint = "worktree 없음 | 같은 스레드 순차 진행"
            result_location = "현재 Codex 운영 스레드"
            waiting_for = "현재 스레드의 다음 응답 또는 같은 대화 안의 후속 보고"
            next_follow_up = "결과를 읽고 완료 기준이 맞으면 같은 스레드에서 바로 다음 티켓이나 단계로 이어갑니다."
        elif effective_mode_id == "thread_automation":
            cadence_hint = preset.cadence_hint or "같은 스레드 heartbeat cadence를 짧게 시작"
            worktree_hint = "보통 worktree 불필요 | 같은 스레드 문맥 유지"
            result_location = "현재 스레드 + thread automation 결과"
            waiting_for = "heartbeat가 다시 스레드를 깨우거나 follow-up 결과가 올라오기를 기다립니다."
            next_follow_up = "현재 스레드와 Automations pane에서 마지막 follow-up 결과를 보고 이어갈지 판단합니다."
        else:
            cadence_hint = preset.cadence_hint or "독립 실행 cadence를 보수적으로 시작"
            worktree_hint = preset.worktree_hint or "코드 수정 가능성이 있으면 background worktree 우선"
            result_location = "Codex Automations pane / Triage / 독립 실행 결과"
            waiting_for = "독립 automation 결과 또는 Triage 항목"
            next_follow_up = "Triage로 재진입해 결과를 읽고, 필요하면 같은 운영 스레드로 후속 handoff를 남깁니다."

        return CodexAutomationModeDecision(
            recommended_mode_id=recommended_mode_id,
            recommended_reason=recommended_reason,
            effective_mode_id=effective_mode_id,
            effective_reason=effective_reason,
            cadence_hint=cadence_hint,
            worktree_hint=worktree_hint,
            result_location=result_location,
            waiting_for=waiting_for,
            next_follow_up=next_follow_up,
        )

    def _build_codex_context_sections(self, session: SessionConfig) -> list[str]:
        steps = session.project.steps()
        step_lines = [f"- {index + 1}. {step}" for index, step in enumerate(steps)]
        rules_text = session.policy.build_rules_for_prompt().strip() or "정책 미입력"
        sections = [
            "[프로젝트 요약]",
            session.project.project_summary.strip() or "프로젝트 요약 미입력",
            "",
            "[목표 수준]",
            session.project.target_outcome.strip() or "목표 수준 미입력",
            "",
            "[단계 목록]",
            "\n".join(step_lines) if step_lines else "- 단계 목록 미입력",
            "",
            "[운영 정책]",
            rules_text,
        ]
        custom_instruction = session.codex_strategy.custom_instruction.strip()
        if custom_instruction:
            sections.extend(
                [
                    "",
                    "[추가 지시 / follow-up 메모]",
                    custom_instruction,
                ]
            )
        return sections

    def _build_no_automation_prompt(self, session: SessionConfig) -> str:
        preset = session.codex_strategy.selected_preset()
        lines = [
            "이 현재 스레드에서 이 프로젝트를 순차적으로 진행해 주세요.",
            "",
            "기본 원칙:",
            "- automation 없이 같은 현재 스레드에서 이어갑니다.",
            "- 한 번에 한 티켓 또는 한 단계만 처리합니다.",
            "- 현재 단계의 완료 기준이 충족될 때만 다음 단계로 넘어갑니다.",
            "- 판단이 continue이면 사용자 추가 입력을 기다리지 말고 바로 다음 단계로 진행합니다.",
            "- 애매하거나 위험하거나 확인이 필요하면 ask_user로 전환합니다.",
            "- 파괴적이거나 되돌리기 어려운 작업 전에는 반드시 멈춥니다.",
            "",
            "완료 기준 판정 방식:",
            "- 해당 단계나 티켓 문서의 목적, 범위, 완료 조건을 기준으로 판단합니다.",
            "- 코드 변경이 있으면 가능한 최소 검증을 수행하고 못 했으면 이유를 적습니다.",
            "",
            "매 응답 형식:",
            "1. 현재 단계 또는 티켓",
            "2. 한 일",
            "3. 검증 결과",
            "4. 판단: continue / pause / ask_user",
            "5. 다음 행동",
            "",
            "[시나리오별 세부 지시]",
            preset.prompt_template.strip(),
        ]
        return "\n".join(lines).strip()

    def _build_thread_automation_prompt(self, session: SessionConfig) -> str:
        preset = session.codex_strategy.selected_preset()
        lines = [
            "현재 스레드 문맥을 유지하는 thread automation용 작업 설명입니다.",
            "",
            "핵심 원칙:",
            "- 현재 스레드를 읽고 지금 단계가 끝났는지 먼저 판단합니다.",
            "- 같은 스레드 문맥을 유지한 채 다음 액션 1개만 제안하거나 진행합니다.",
            "- 애매하면 보류하고, ask_user가 필요하면 바로 멈춥니다.",
            "- schedule이나 cadence는 automation 설정에서 따로 넣고, 이 prompt에는 작업 자체만 적습니다.",
            "",
            "매 실행 보고 형식:",
            "1. 현재 상태",
            "2. 진행 또는 보류 판단",
            "3. 다음 액션",
            "4. 위험 또는 확인 필요",
            "",
            "[시나리오별 세부 지시]",
            preset.prompt_template.strip(),
        ]
        return "\n".join(lines).strip()

    def _build_project_automation_prompt(self, session: SessionConfig) -> str:
        preset = session.codex_strategy.selected_preset()
        lines = [
            "이 프로젝트에 대한 독립 project automation용 작업 설명입니다.",
            "",
            "핵심 원칙:",
            "- 각 실행은 독립 보고처럼 동작합니다.",
            "- 현재 프로젝트 상태를 기준으로 가장 중요한 점검이나 triage만 짧게 수행합니다.",
            "- 확신이 낮으면 추정이라고 적고, 사람 확인이 필요하면 ask_user 성격으로 분리합니다.",
            "- worktree 여부와 cadence는 automation 설정에서 따로 고르고, 이 prompt에는 해야 할 일만 적습니다.",
            "",
            "매 실행 보고 형식:",
            "1. 실행한 일",
            "2. 통과/실패 또는 변화 요약",
            "3. 바로 이어갈 수 있는 다음 액션",
            "4. 상단장님 확인 필요 사항",
            "",
            "[시나리오별 세부 지시]",
            preset.prompt_template.strip(),
        ]
        return "\n".join(lines).strip()

    def build_codex_strategy_prompt(
        self,
        session: SessionConfig,
        runtime: RuntimeState | None = None,
    ) -> str:
        preset = get_codex_automation_preset(session.codex_strategy.selected_preset_id)
        decision = self.recommend_codex_automation_mode(session, runtime)
        recommended_option = get_codex_automation_mode_option(decision.recommended_mode_id)
        effective_option = get_codex_automation_mode_option(decision.effective_mode_id)
        if decision.effective_mode_id == "thread_automation":
            launch_prompt = self._build_thread_automation_prompt(session)
        elif decision.effective_mode_id == "project_automation":
            launch_prompt = self._build_project_automation_prompt(session)
        else:
            launch_prompt = self._build_no_automation_prompt(session)

        sections = [
            "[추천 시나리오]",
            preset.title,
            "",
            "[추천 mode]",
            recommended_option.title,
            "",
            "[추천 이유]",
            decision.recommended_reason,
            "",
            "[현재 선택 mode]",
            effective_option.title,
            "",
            "[현재 launch 방향]",
            decision.effective_reason,
            "",
            "[cadence 힌트]",
            decision.cadence_hint,
            "",
            "[worktree 힌트]",
            decision.worktree_hint,
            "",
            "[결과를 다시 볼 위치]",
            decision.result_location,
            "",
            "[이 시나리오를 쓰는 상황]",
            preset.use_when,
        ]
        sections.extend([""] + self._build_codex_context_sections(session))
        sections.extend(["", "[Launch-ready prompt 초안]", launch_prompt])
        return "\n".join(sections).strip()

    def build_codex_strategy_runbook(
        self,
        session: SessionConfig,
        runtime: RuntimeState | None = None,
    ) -> str:
        preset = get_codex_automation_preset(session.codex_strategy.selected_preset_id)
        decision = self.recommend_codex_automation_mode(session, runtime)
        effective_option = get_codex_automation_mode_option(decision.effective_mode_id)
        lines = [
            "[운영 런북 / handoff]",
            f"전략: {preset.title}",
            f"현재 mode: {effective_option.title}",
            "",
            "1. 현재 프로젝트 요약, 목표, 단계 목록이 최신 상태인지 먼저 확인합니다.",
            "2. Codex 전략 탭의 Launch-ready prompt 초안을 복사합니다.",
            f"3. cadence는 {decision.cadence_hint} 기준으로 시작합니다.",
            f"4. worktree는 {decision.worktree_hint} 기준으로 판단합니다.",
            f"5. 결과 재진입 위치는 {decision.result_location} 입니다.",
            "",
            "[이 프리셋에서 Codex가 할 일]",
            preset.codex_role,
            "",
            "[이 프리셋에서 javis가 덮을 일]",
            preset.javis_role,
            "",
            "[실전 handoff 순서]",
        ]

        if decision.effective_mode_id == "thread_automation":
            lines.extend(
                [
                    "- 현재 Codex 운영 스레드를 연 상태에서 thread automation 생성 화면으로 들어갑니다.",
                    "- launch prompt를 붙여 넣고, cadence는 너무 촘촘하지 않게 보수적으로 시작합니다.",
                    "- 결과는 같은 스레드와 thread heartbeat 결과를 함께 다시 확인합니다.",
                ]
            )
        elif decision.effective_mode_id == "project_automation":
            lines.extend(
                [
                    "- Codex project automation 생성 화면으로 이동해 독립 실행 작업으로 만듭니다.",
                    "- standalone / project automation으로 분리해 결과를 Triage 쪽에서 다시 읽는 흐름을 기본으로 봅니다.",
                    "- 코드 수정 가능성이 있으면 local 작업본 대신 background worktree를 우선 검토합니다.",
                    "- 결과는 Automations pane 또는 Triage에서 다시 읽고, 필요하면 운영 스레드에 후속 handoff를 남깁니다.",
                ]
            )
        else:
            lines.extend(
                [
                    "- automation을 만들지 않고 현재 운영 스레드에 launch prompt를 바로 붙여 넣습니다.",
                    "- 판단이 continue면 사용자 추가 입력 없이 같은 스레드에서 다음 티켓으로 이어가게 합니다.",
                    "- 결과는 같은 스레드에서 바로 읽고 필요 시 ask_user로 멈춥니다.",
                ]
            )

        lines.extend(
            [
                "- 첫 실행은 항상 수동으로 한 번 검토합니다.",
                "- 결과 형식이 과도하게 길거나 애매하면 prompt 초안을 짧게 다듬습니다.",
                "- 반복 실패, 삭제 위험, 배포 위험이 보이면 자동 진행보다 ask_user가 우선입니다.",
                "",
                "[후속 체크리스트]",
                "- prompt 초안이 현재 프로젝트 목표와 단계를 제대로 반영하는가",
                "- 보고 형식이 짧고 운영자 친화적인가",
                "- 결과를 다시 볼 위치가 분명한가",
                "- automation 없이도 충분한 상황은 아닌가",
            ]
        )
        return "\n".join(lines).strip()

    def build_automation_runboard(self, session: SessionConfig, runtime: RuntimeState) -> str:
        preset = get_codex_automation_preset(session.codex_strategy.selected_preset_id)
        decision = self.recommend_codex_automation_mode(session, runtime)
        recommended_option = get_codex_automation_mode_option(decision.recommended_mode_id)
        effective_option = get_codex_automation_mode_option(decision.effective_mode_id)
        steps = session.project.steps()
        total_steps = len(steps)
        completed_steps = min(runtime.next_step_index, total_steps)
        if total_steps == 0:
            progress_line = "단계 정보가 아직 없어 운영 진행 상태를 계산하지 못했습니다."
        elif runtime.next_step_index >= total_steps:
            progress_line = f"현재 계획을 모두 전송했습니다. 진행 {completed_steps}/{total_steps}"
        else:
            current_step = steps[runtime.next_step_index]
            progress_line = f"현재 단계 {runtime.next_step_index + 1}/{total_steps}: {current_step}"

        lines = [
            "[Automation Runboard]",
            f"전략: {preset.title}",
            f"현재 mode: {effective_option.title}",
            f"추천 mode: {recommended_option.title}",
            "",
            "[지금 무엇을 기다리는가]",
            decision.waiting_for,
            "",
            "[최근 follow-up 메모]",
            session.codex_strategy.custom_instruction.strip() or "추가 지시 / follow-up 메모 없음",
            "",
            "[현재 진행 상태]",
            progress_line,
            "",
            "[마지막 상태 신호]",
            runtime.last_target_reason or "최근 상태 신호 없음",
            "",
            "[다음 확인 행동]",
            decision.next_follow_up,
        ]
        return "\n".join(lines).strip()

    def build_triage_summary_bridge(self, session: SessionConfig, runtime: RuntimeState) -> str:
        decision = self.recommend_codex_automation_mode(session, runtime)
        effective_option = get_codex_automation_mode_option(decision.effective_mode_id)
        lines = [
            "[Triage / Re-entry Bridge]",
            f"현재 mode: {effective_option.title}",
            "",
            "[어디를 다시 열어볼지]",
            decision.result_location,
            "",
            "[무엇을 먼저 볼지]",
        ]
        if decision.effective_mode_id == "project_automation":
            lines.extend(
                [
                    "- 최신 automation 실행 결과 제목과 통과/실패 요약",
                    "- 실패 원인 후보, 다음 액션, ask_user 성격 메모",
                    "- 필요하면 다시 같은 운영 스레드로 handoff할 내용",
                ]
            )
        else:
            lines.extend(
                [
                    "- 현재 단계 보고와 검증 결과",
                    "- continue / pause / ask_user 판단",
                    "- 다음 단계로 바로 이어도 되는지 여부",
                ]
            )
        lines.extend(
            [
                "",
                "[다음 follow-up 제안]",
                decision.next_follow_up,
                "",
                "[멈춰야 하는 신호]",
                "- ask_user 또는 pause가 올라온 경우",
                "- 삭제, 배포, 과금, 반복 실패처럼 되돌리기 어려운 위험이 보이는 경우",
            ]
        )
        return "\n".join(lines).strip()

    def build_native_fallback_matrix(
        self,
        session: SessionConfig,
        runtime: RuntimeState | None = None,
    ) -> str:
        active_runtime = runtime or RuntimeState()
        preset = get_codex_automation_preset(session.codex_strategy.selected_preset_id)
        decision = self.recommend_codex_automation_mode(session, active_runtime)
        recommended_option = get_codex_automation_mode_option(decision.recommended_mode_id)
        lines = [
            "[Automation Safety Guard]",
            f"현재 전략: {preset.title}",
            f"추천 mode: {recommended_option.title}",
            "",
            "[no automation을 먼저 보는 경우]",
            "- 마스터플랜이 이미 있고 단계나 티켓을 순차 진행하기만 하면 되는 경우",
            "- 같은 스레드에서 바로 결과를 보고 이어갈 수 있어 cadence가 꼭 필요 없는 경우",
            "- 운영 복잡도를 늘리지 않고 Codex 네이티브 흐름만으로 충분한 경우",
            "",
            "[stop / ask_user 조건]",
            "- 파괴적이거나 되돌리기 어려운 작업",
            "- 확신이 낮고 추정이 많은 상태",
            "- 같은 실패가 반복되는 상태",
            "- 사람 확인이 필요한 배포, 삭제, 과금, 권한 변경 위험",
            "",
            "[현재 전략 기준 메모]",
            f"- cadence 힌트: {decision.cadence_hint}",
            f"- worktree 힌트: {decision.worktree_hint}",
            f"- 결과 재진입 위치: {decision.result_location}",
            "",
            "[Native vs Fallback 안전 매트릭스]",
            f"현재 전략: {preset.title}",
            "",
            "[먼저 Codex 네이티브 경로를 쓰는 경우]",
            f"- 추천 경로: {recommended_option.title}",
            "- 같은 스레드 문맥, project automation, worktree, review queue, skills로 충분히 해결 가능할 때",
            "- 단순한 단계 진행, nightly brief, smoke, triage처럼 Codex가 이미 잘하는 반복 작업일 때",
            "",
            "[로컬 데스크톱 fallback을 고려하는 경우]",
            "- Codex 네이티브 경로로는 화면 확인이나 브라우저 상태 감시가 부족할 때",
            "- 팝업이 즉시 보조해야 해서 desktop surface가 직접 신호를 보여줘야 할 때",
            "- Codex 앱 밖의 상태를 한 번 더 읽어야 판단이 가능할 때",
            "",
            "[자동 진행보다 멈춤이 우선인 경우]",
            "- 파괴적이거나 되돌리기 어려운 작업",
            "- 확신이 낮고 추정이 많은 상태",
            "- 같은 실패가 반복되는 상태",
            "- 사람 확인이 필요한 배포/과금/삭제 위험",
            "",
            "[이 전략에서의 주의 메모]",
            f"- cadence 힌트: {decision.cadence_hint}",
            f"- worktree 힌트: {decision.worktree_hint}",
            "- 원칙: 네이티브 우선, fallback 보조, 애매하면 보류",
        ]
        return "\n".join(lines).strip()

    def _resolve_deep_integration_readiness(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
    ) -> tuple[str, str]:
        app_server_id = session.deep_integration.app_server_readiness_id
        cloud_trigger_id = session.deep_integration.cloud_trigger_readiness_id
        automation_decision = self.recommend_codex_automation_mode(session, runtime)

        if app_server_id == "auto":
            if automation_decision.effective_mode_id == "project_automation":
                app_server_id = "limited"
            else:
                app_server_id = "limited"

        if cloud_trigger_id == "auto":
            if automation_decision.effective_mode_id in {"thread_automation", "project_automation"}:
                cloud_trigger_id = "limited"
            else:
                cloud_trigger_id = "unavailable"

        return app_server_id, cloud_trigger_id

    def recommend_deep_integration_mode(
        self,
        session: SessionConfig,
        runtime: RuntimeState,
    ) -> DeepIntegrationModeDecision:
        automation_decision = self.recommend_codex_automation_mode(session, runtime)
        app_server_id, cloud_trigger_id = self._resolve_deep_integration_readiness(session, runtime)
        app_server_option = get_deep_integration_readiness_option(app_server_id)
        cloud_trigger_option = get_deep_integration_readiness_option(cloud_trigger_id)
        steps = session.project.steps()

        if app_server_id == "ready":
            recommended_mode_id = "app_server_assisted"
            recommended_reason = (
                "App Server readiness가 준비됨으로 표시되어 있어, 가장 얇고 직접적인 native handoff 경로를 먼저 검토하는 편이 맞습니다."
            )
        elif cloud_trigger_id == "ready":
            recommended_mode_id = "cloud_trigger_supervision"
            recommended_reason = (
                "cloud trigger readiness가 준비됨으로 표시되어 있어, javis는 polling보다 watch/re-entry 감독에 집중하는 편이 좋습니다."
            )
        else:
            recommended_mode_id = "native_app_assisted"
            recommended_reason = (
                "현재는 Codex app / automation / triage 같은 네이티브 흐름이 가장 안정적이므로, deep integration도 app-assisted 경로를 기본으로 보는 편이 안전합니다."
            )

        selected_mode_id = session.deep_integration.selected_mode_id
        effective_mode_id = recommended_mode_id if selected_mode_id == "recommended" else selected_mode_id
        effective_reason = recommended_reason if selected_mode_id == "recommended" else (
            f"상단장님이 deep integration mode를 {get_deep_integration_mode_option(selected_mode_id).title}로 직접 고정했습니다."
        )

        if effective_mode_id == "desktop_fallback" and not session.deep_integration.desktop_fallback_allowed:
            effective_mode_id = recommended_mode_id
            effective_reason = "desktop fallback 허용이 꺼져 있어, 수동 override 대신 추천 native 경로로 되돌렸습니다."

        if runtime.operator_paused or runtime.last_judgment.decision in {"ask_user", "pause"}:
            supervisor_state = "escalate"
            supervisor_reason = runtime.operator_pause_reason or runtime.last_judgment.message_to_user or "사람 확인이 필요한 신호가 있어 escalate 상태입니다."
        elif effective_mode_id == "desktop_fallback" and session.deep_integration.desktop_fallback_allowed:
            supervisor_state = "fallback"
            supervisor_reason = "native 경로가 아니라 desktop fallback을 예외적으로 운영 경로에 올린 상태입니다."
        elif runtime.auto_running:
            supervisor_state = "watch"
            supervisor_reason = "자동 루프가 돌고 있어 javis가 현재 흐름을 감시하는 watch 상태입니다."
        elif runtime.voice_pending_action_id:
            supervisor_state = "waiting"
            supervisor_reason = "voice confirmation이 남아 있어 다음 액션 전 waiting 상태입니다."
        elif not steps or not runtime.last_target_title:
            supervisor_state = "sleep"
            supervisor_reason = "현재 프로젝트 단계 또는 타깃 창이 충분히 준비되지 않아 sleep 상태로 보는 편이 맞습니다."
        elif automation_decision.effective_mode_id == "project_automation":
            supervisor_state = "re_enter"
            supervisor_reason = "독립 실행 결과를 다시 받아 재진입해야 하는 흐름이라 re-enter 상태가 핵심입니다."
        elif runtime.next_step_index >= len(steps):
            supervisor_state = "waiting"
            supervisor_reason = "현재 계획 전송이 모두 끝나 결과 검토나 다음 계획 입력을 기다리는 상태입니다."
        else:
            supervisor_state = "watch"
            supervisor_reason = "현재 프로젝트와 Codex 타깃이 준비되어 있어 상위 감독 watch 상태로 보는 편이 자연스럽습니다."

        if not session.deep_integration.desktop_fallback_allowed:
            fallback_state = "blocked"
            fallback_reason = "desktop fallback 허용이 꺼져 있어 native 경로가 우선이고 local fallback은 차단된 상태입니다."
        elif effective_mode_id == "desktop_fallback":
            fallback_state = "active"
            fallback_reason = "현재 선택된 deep integration mode가 desktop fallback이라 예외 경로가 활성화된 상태입니다."
        else:
            fallback_state = "standby"
            fallback_reason = "desktop fallback은 예외 경로로만 대기 중이며, 현재는 native 중심 흐름을 사용합니다."

        if effective_mode_id == "app_server_assisted":
            handoff_target = "App Server handoff bundle"
            reentry_source = "App Server result / handoff"
            next_review_point = "App Server handoff 성공 여부와 재진입 상태를 확인합니다."
        elif effective_mode_id == "cloud_trigger_supervision":
            handoff_target = "Codex cloud follow-up / triage"
            reentry_source = "cloud trigger result"
            next_review_point = "cloud follow-up 결과와 triage 재진입 신호를 확인합니다."
        elif effective_mode_id == "desktop_fallback":
            handoff_target = "local popup / desktop surface"
            reentry_source = "local desktop fallback"
            next_review_point = "fallback 해제 가능 여부와 native 복귀 조건을 확인합니다."
        else:
            handoff_target = automation_decision.result_location
            reentry_source = "current thread / app-native result"
            next_review_point = automation_decision.next_follow_up

        return DeepIntegrationModeDecision(
            recommended_mode_id=recommended_mode_id,
            recommended_reason=recommended_reason,
            effective_mode_id=effective_mode_id,
            effective_reason=effective_reason,
            app_server_readiness_id=app_server_option.readiness_id,
            cloud_trigger_readiness_id=cloud_trigger_option.readiness_id,
            supervisor_state=supervisor_state,
            supervisor_reason=supervisor_reason,
            fallback_state=fallback_state,
            fallback_reason=fallback_reason,
            handoff_target=handoff_target,
            reentry_source=reentry_source,
            next_review_point=next_review_point,
        )

    def build_deep_integration_capability_registry(self, session: SessionConfig, runtime: RuntimeState) -> str:
        automation_decision = self.recommend_codex_automation_mode(session, runtime)
        decision = self.recommend_deep_integration_mode(session, runtime)
        app_server_option = get_deep_integration_readiness_option(decision.app_server_readiness_id)
        cloud_trigger_option = get_deep_integration_readiness_option(decision.cloud_trigger_readiness_id)
        payload = {
            "project": {
                "summary": session.project.project_summary.strip(),
                "target_outcome": session.project.target_outcome.strip(),
                "steps_total": len(session.project.steps()),
            },
            "capability_registry": {
                "codex_app_native": automation_decision.effective_mode_id,
                "app_server_readiness": {
                    "id": app_server_option.readiness_id,
                    "title": app_server_option.title,
                    "notes": session.deep_integration.app_server_notes.strip(),
                },
                "cloud_trigger_readiness": {
                    "id": cloud_trigger_option.readiness_id,
                    "title": cloud_trigger_option.title,
                    "notes": session.deep_integration.cloud_trigger_notes.strip(),
                },
                "desktop_fallback_allowed": session.deep_integration.desktop_fallback_allowed,
            },
            "deep_integration": {
                "recommended_mode": get_deep_integration_mode_option(decision.recommended_mode_id).title,
                "selected_mode": session.deep_integration.selected_mode().title,
                "effective_mode": get_deep_integration_mode_option(decision.effective_mode_id).title,
                "supervisor_state": decision.supervisor_state,
                "fallback_state": decision.fallback_state,
            },
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def build_cross_surface_handoff_bundle(self, session: SessionConfig, runtime: RuntimeState) -> str:
        decision = self.recommend_deep_integration_mode(session, runtime)
        automation_decision = self.recommend_codex_automation_mode(session, runtime)
        preview = self.build_prompt_preview(session, runtime)
        steps = session.project.steps()
        current_step = preview.step_title or ("모든 단계 전송 완료" if runtime.next_step_index >= len(steps) and steps else "다음 단계 없음")
        lines = [
            "[Cross-Surface Handoff Bundle]",
            f"프로젝트: {session.project.project_summary or session.project.target_outcome or '미입력'}",
            f"현재 단계: {current_step}",
            f"자동화 경로: {get_codex_automation_mode_option(automation_decision.effective_mode_id).title}",
            f"deep integration mode: {get_deep_integration_mode_option(decision.effective_mode_id).title}",
            f"supervisor state: {decision.supervisor_state}",
            f"handoff target: {decision.handoff_target}",
            f"re-entry source: {decision.reentry_source}",
            "",
            "[현재 리스크 / 멈춤 신호]",
            runtime.operator_pause_reason or runtime.last_judgment.message_to_user or runtime.last_visual_result.message_to_user or "명시된 멈춤 신호 없음",
            "",
            "[마지막 판단]",
            runtime.last_judgment.message_to_user or runtime.last_judgment.reason or "판단 결과 없음",
            "",
            "[마지막 시각/음성 메모]",
            runtime.last_visual_result.message_to_user or runtime.last_voice_result.message_to_user or "추가 evidence 메모 없음",
            "",
            "[handoff note]",
            session.deep_integration.handoff_notes.strip() or "추가 handoff note 없음",
            "",
            "[다음 review point]",
            decision.next_review_point,
        ]
        return "\n".join(lines).strip()

    def build_integration_observability_report(self, session: SessionConfig, runtime: RuntimeState) -> str:
        decision = self.recommend_deep_integration_mode(session, runtime)
        automation_decision = self.recommend_codex_automation_mode(session, runtime)
        app_server_option = get_deep_integration_readiness_option(decision.app_server_readiness_id)
        cloud_trigger_option = get_deep_integration_readiness_option(decision.cloud_trigger_readiness_id)
        lines = [
            "[Deep Integration Observability]",
            f"추천 mode: {get_deep_integration_mode_option(decision.recommended_mode_id).title}",
            f"실제 mode: {get_deep_integration_mode_option(decision.effective_mode_id).title}",
            f"Codex automation mode: {get_codex_automation_mode_option(automation_decision.effective_mode_id).title}",
            "",
            "[Readiness]",
            f"- App Server: {app_server_option.title}",
            f"- Cloud Trigger: {cloud_trigger_option.title}",
            "",
            "[Supervisor]",
            f"- 상태: {decision.supervisor_state}",
            f"- 이유: {decision.supervisor_reason}",
            "",
            "[Fallback]",
            f"- 상태: {decision.fallback_state}",
            f"- 이유: {decision.fallback_reason}",
            "",
            "[Re-entry]",
            f"- source: {decision.reentry_source}",
            f"- target: {decision.handoff_target}",
            f"- next review: {decision.next_review_point}",
            "",
            "[운영 메모]",
            session.deep_integration.app_server_notes.strip() or session.deep_integration.cloud_trigger_notes.strip() or "추가 운영 메모 없음",
        ]
        return "\n".join(lines).strip()

    def recommend_live_ops_status(self, session: SessionConfig, runtime: RuntimeState) -> LiveOpsStatusDecision:
        automation_decision = self.recommend_codex_automation_mode(session, runtime)
        deep_decision = self.recommend_deep_integration_mode(session, runtime)
        profile = session.live_ops.selected_profile()
        cadence = session.live_ops.selected_report_cadence()
        reentry = session.live_ops.selected_reentry_mode()
        steps = session.project.steps()
        steps_remaining = max(len(steps) - runtime.next_step_index, 0)

        if runtime.operator_paused or runtime.last_judgment.decision in {"ask_user", "pause"}:
            lane_id = "blocked"
            lane_reason = runtime.operator_pause_reason or runtime.last_judgment.message_to_user or "사람 확인이 필요한 멈춤 신호가 있어 blocked lane으로 둡니다."
        elif runtime.voice_pending_action_id:
            lane_id = "manual_review"
            lane_reason = "voice confirmation이나 수동 확인이 남아 있어 manual review lane으로 둡니다."
        elif runtime.auto_running:
            lane_id = "active_run"
            lane_reason = "현재 자동 루프가 돌고 있어 javis는 결과를 지켜보는 active run lane에 있습니다."
        elif automation_decision.effective_mode_id != "no_automation" and (
            runtime.last_judgment.has_result or runtime.last_visual_result.has_result or runtime.last_voice_result.has_result
        ):
            lane_id = "reentry_ready"
            lane_reason = "automation이나 follow-up 결과가 쌓여 있어 운영 스레드로 다시 들어갈 re-entry ready lane입니다."
        elif automation_decision.effective_mode_id != "no_automation":
            lane_id = "waiting_result"
            lane_reason = "Codex native / automation 결과를 기다리는 waiting result lane입니다."
        elif steps_remaining > 0 and runtime.last_target_title:
            lane_id = "launch_ready"
            lane_reason = "현재 프로젝트와 타겟 창이 준비되어 있어 바로 launch하거나 다음 단계로 이어갈 수 있습니다."
        else:
            lane_id = "manual_review"
            lane_reason = "프로젝트 정보나 타겟 환경이 아직 덜 준비되어 있어 운영자가 한 번 더 점검해야 합니다."

        if lane_id == "blocked":
            operator_touchpoint = "현재 멈춤 이유를 읽고, 복구 플레이북 또는 ask_user 흐름으로 정리합니다."
            recovery_level = "manual"
            recovery_reason = "리스크 / 보류 / 수동 승인 신호가 있어 자동 재진입보다 사람 확인이 우선입니다."
        elif lane_id == "manual_review":
            operator_touchpoint = "런치 전 설정, confirmation, 정책 메모를 다시 확인합니다."
            recovery_level = "guided"
            recovery_reason = "설정과 확인 포인트를 맞추면 다시 자동 흐름으로 진입할 수 있습니다."
        elif lane_id == "reentry_ready":
            operator_touchpoint = f"{reentry.title} 기준으로 결과를 읽고, 다음 티켓 또는 다음 단계로 재진입합니다."
            recovery_level = "light"
            recovery_reason = "이미 결과가 있어 재진입 브리프를 읽고 같은 흐름으로 이어가면 됩니다."
        elif lane_id == "waiting_result":
            operator_touchpoint = "Triage / thread / project 결과를 기다렸다가 재진입 브리프로 이어갑니다."
            recovery_level = "none"
            recovery_reason = "지금은 추가 조작보다 결과 수집과 watch가 우선입니다."
        elif lane_id == "active_run":
            operator_touchpoint = "현재 자동 루프를 건드리지 말고 milestone 또는 risk 신호만 지켜봅니다."
            recovery_level = "none"
            recovery_reason = "현재는 recovery보다 bounded supervision이 더 중요합니다."
        else:
            operator_touchpoint = "운영 차터와 런치패드를 확인하고 Codex 실행을 시작합니다."
            recovery_level = "light"
            recovery_reason = "런치 직전 점검만 끝나면 현재 스레드나 automation으로 바로 넘길 수 있습니다."

        if profile.profile_id == "guarded":
            report_style = "보수 운용 | 중요한 단계와 위험 신호마다 짧은 운영 보고"
        elif profile.profile_id == "hands_off":
            report_style = f"{cadence.title} | Codex가 더 길게 달리고 javis는 예외와 재진입 중심"
        else:
            report_style = f"{cadence.title} | 마일스톤 중심의 감독 흐름"

        if reentry.reentry_id == "triage_first":
            reentry_action = "Triage / Automations 결과를 먼저 읽고, 필요한 내용만 운영 스레드에 handoff합니다."
        elif reentry.reentry_id == "manual_gate":
            reentry_action = "javis가 결과를 먼저 검토한 뒤 운영 게이트를 통과시킨 후 재진입합니다."
        else:
            reentry_action = "같은 운영 스레드로 돌아와 바로 다음 단계 판단과 후속 지시를 이어갑니다."

        if steps_remaining > session.live_ops.max_unattended_steps and profile.profile_id != "hands_off":
            reentry_action += f" 현재 남은 단계가 {steps_remaining}개라, {session.live_ops.max_unattended_steps}단계 이하로 다시 끊는 편이 안전합니다."

        if deep_decision.supervisor_state == "escalate" and lane_id not in {"blocked", "manual_review"}:
            lane_id = "manual_review"
            lane_reason = "Deep Integration supervisor가 escalate를 요구해 live ops lane도 manual review로 올립니다."
            operator_touchpoint = "Deep Integration handoff와 현재 리스크를 먼저 읽고 재시작 여부를 결정합니다."
            recovery_level = "manual"
            recovery_reason = "integration 레벨에서 이미 사람 확인이 필요한 신호가 올라왔습니다."

        return LiveOpsStatusDecision(
            lane_id=lane_id,
            lane_reason=lane_reason,
            operator_touchpoint=operator_touchpoint,
            report_style=report_style,
            reentry_action=reentry_action,
            recovery_level=recovery_level,
            recovery_reason=recovery_reason,
        )

    def build_live_ops_charter(self, session: SessionConfig, runtime: RuntimeState) -> str:
        automation_decision = self.recommend_codex_automation_mode(session, runtime)
        deep_decision = self.recommend_deep_integration_mode(session, runtime)
        ops = self.recommend_live_ops_status(session, runtime)
        lines = [
            "[라이브 오퍼레이션 차터]",
            f"project: {session.project.project_summary or session.project.target_outcome or '미입력'}",
            f"운영 프로필: {session.live_ops.selected_profile().title}",
            f"보고 주기: {session.live_ops.selected_report_cadence().title}",
            f"재진입 방식: {session.live_ops.selected_reentry_mode().title}",
            f"Codex 모드: {get_codex_automation_mode_option(automation_decision.effective_mode_id).title}",
            f"딥 통합 경로: {get_deep_integration_mode_option(deep_decision.effective_mode_id).title}",
            "",
            "[운영 규칙]",
            "- 한 번에 한 단계 또는 한 티켓만 확실히 앞으로 보냅니다.",
            "- 완료 기준이 맞으면 이어가고, 애매하면 pause 또는 ask_user로 멈춥니다.",
            "- 위험 신호, 재시도 루프, fallback 진입 이유는 짧게라도 꼭 남깁니다.",
            f"- 운영 보고 스타일: {ops.report_style}",
            f"- 재진입 방식: {ops.reentry_action}",
            f"- 무인 진행 허용 폭: 최대 {session.live_ops.max_unattended_steps}단계",
            "",
            "[운영 메모]",
            session.live_ops.operator_note.strip() or "추가 운영 메모 없음",
        ]
        return "\n".join(lines).strip()

    def build_live_ops_launchpad(self, session: SessionConfig, runtime: RuntimeState) -> str:
        preview = self.build_prompt_preview(session, runtime)
        automation_decision = self.recommend_codex_automation_mode(session, runtime)
        deep_decision = self.recommend_deep_integration_mode(session, runtime)
        ops = self.recommend_live_ops_status(session, runtime)
        lines = [
            "[라이브 오퍼레이션 런치패드]",
            f"현재 레인: {ops.lane_id}",
            f"레인 사유: {ops.lane_reason}",
            f"다음 단계: {preview.step_title or '다음 단계 없음'}",
            "",
            "[런치 체크리스트]",
            f"1. Codex 실행 방식 확인: {get_codex_automation_mode_option(automation_decision.effective_mode_id).title}",
            f"2. Deep integration 경로 확인: {get_deep_integration_mode_option(deep_decision.effective_mode_id).title}",
            f"3. 운영자 터치포인트 확인: {ops.operator_touchpoint}",
            f"4. 재진입 방식 확인: {session.live_ops.selected_reentry_mode().title}",
            "",
            "[즉시 행동]",
            preview.draft_prompt.strip() or "프롬프트 새로고침 후 현재 단계 launch prompt를 준비합니다.",
        ]
        return "\n".join(lines).strip()

    def build_live_ops_reentry_brief(self, session: SessionConfig, runtime: RuntimeState) -> str:
        ops = self.recommend_live_ops_status(session, runtime)
        automation_decision = self.recommend_codex_automation_mode(session, runtime)
        lines = [
            "[라이브 오퍼레이션 재진입 브리프]",
            f"현재 레인: {ops.lane_id}",
            f"Codex 모드: {get_codex_automation_mode_option(automation_decision.effective_mode_id).title}",
            f"재진입 방식: {session.live_ops.selected_reentry_mode().title}",
            "",
            "[먼저 읽기]",
            runtime.last_judgment.message_to_user or runtime.last_judgment.reason or runtime.last_visual_result.message_to_user or "우선 읽을 판단 메모 없음",
            "",
            "[이어서 할 일]",
            ops.reentry_action,
            "",
            "[주의할 점]",
            runtime.operator_pause_reason or runtime.last_visual_result.contradiction_reason or runtime.last_voice_result.message_to_user or "명시된 재진입 리스크 없음",
        ]
        return "\n".join(lines).strip()

    def build_live_ops_recovery_playbook(self, session: SessionConfig, runtime: RuntimeState) -> str:
        ops = self.recommend_live_ops_status(session, runtime)
        lines = [
            "[라이브 오퍼레이션 복구 플레이북]",
            f"복구 단계: {ops.recovery_level}",
            f"사유: {ops.recovery_reason}",
            "",
            "[기본 복구 흐름]",
        ]
        if ops.recovery_level == "manual":
            lines.extend(
                [
                    "- 현재 멈춤 이유와 last judgment / visual note를 먼저 읽습니다.",
                    "- 파괴적 작업 전 승인, 재시도 프롬프트, fallback 허용 여부를 다시 확인합니다.",
                    "- 필요하면 ask_user 또는 manual gate로 전환합니다.",
                ]
            )
        elif ops.recovery_level == "guided":
            lines.extend(
                [
                    "- 운영 메모와 현재 lane reason을 읽고 작은 범위의 재진입부터 시도합니다.",
                    "- deep integration과 codex mode가 현재 상황에 맞는지 다시 고릅니다.",
                    "- 재시작 전에 런북과 re-entry brief를 같이 확인합니다.",
                ]
            )
        elif ops.recovery_level == "light":
            lines.extend(
                [
                    "- 결과를 같은 운영 스레드 또는 triage에서 다시 읽습니다.",
                    "- 현재 단계를 넘겨도 되는지 짧게 판단하고 바로 이어갑니다.",
                ]
            )
        else:
            lines.extend(
                [
                    "- 현재는 recovery보다 관찰과 bounded supervision이 우선입니다.",
                    "- 다음 review point가 올 때까지 과한 개입을 피합니다.",
                ]
            )
        lines.extend(["", "[참고 메모]", session.live_ops.operator_note.strip() or "추가 운영 메모 없음"])
        return "\n".join(lines).strip()

    def build_live_ops_shift_brief(self, session: SessionConfig, runtime: RuntimeState) -> str:
        ops = self.recommend_live_ops_status(session, runtime)
        lines = [
            "[라이브 오퍼레이션 시프트 브리프]",
            f"프로젝트: {session.project.project_summary or session.project.target_outcome or '미입력'}",
            f"현재 레인: {ops.lane_id}",
            f"터치포인트: {ops.operator_touchpoint}",
            f"보고 스타일: {ops.report_style}",
            f"복구 단계: {ops.recovery_level}",
            f"최근 메모: {runtime.last_judgment.message_to_user or runtime.last_visual_result.message_to_user or runtime.last_voice_result.message_to_user or '특이 사항 없음'}",
        ]
        return "\n".join(lines).strip()

    def _resolve_input_click(self, session: SessionConfig, handle: int) -> tuple[int, int]:
        rect = self.bridge.get_window_rect(handle)
        return session.automation.resolve_click_offset(
            actual_width=rect.width,
            actual_height=rect.height,
        )

    def _remember_target(self, session: SessionConfig, resolution: WindowResolution) -> None:
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

    def _sync_runtime_target(self, runtime: RuntimeState, resolution: WindowResolution) -> None:
        runtime.last_target_title = resolution.selected.title if resolution.selected else ""
        runtime.last_target_reason = resolution.summary()
        runtime.last_target_score = resolution.score if resolution.selected else None
        runtime.target_lock_status = resolution.lock_status
