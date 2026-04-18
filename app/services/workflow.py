from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from app.automation.bmp import compute_signature, normalized_distance
from app.automation.windows_ui import WindowResolution, WindowsDesktopBridge
from app.models import CycleReport, RuntimeState, SessionConfig


class AutomationEngine:
    def __init__(self, bridge: WindowsDesktopBridge, capture_dir: Path) -> None:
        self.bridge = bridge
        self.capture_dir = capture_dir

    def run_cycle(self, session: SessionConfig, runtime: RuntimeState) -> CycleReport:
        resolution = self.bridge.resolve_target(session.window)
        self._sync_runtime_target(runtime, resolution)
        if resolution.selected is None:
            runtime.reset_stability()
            return CycleReport(
                window_found=False,
                message=resolution.summary(),
                target_reason=resolution.reason_text,
                target_score=None,
                lock_status=resolution.lock_status,
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

        prompt = self.build_step_prompt(session, runtime.next_step_index)
        if session.automation.dry_run:
            report.action_taken = True
            report.step_sent = prompt
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
        self._remember_target(session, resolution)
        report.action_taken = True
        report.step_sent = prompt
        report.message = f"{resolution.summary()} 다음 단계 {runtime.next_step_index}개째를 Codex에 전송했습니다."
        return report

    def send_next_step_now(self, session: SessionConfig, runtime: RuntimeState) -> CycleReport:
        resolution = self.bridge.resolve_target(session.window)
        self._sync_runtime_target(runtime, resolution)
        if resolution.selected is None:
            return CycleReport(
                window_found=False,
                message=resolution.summary(),
                target_reason=resolution.reason_text,
                target_score=None,
                lock_status=resolution.lock_status,
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

        prompt = self.build_step_prompt(session, runtime.next_step_index)
        if session.automation.dry_run:
            runtime.last_action_at = time.time()
            runtime.stable_cycles = 0
            return CycleReport(
                window_found=True,
                window_title=target.title,
                action_taken=True,
                step_sent=prompt,
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
        return CycleReport(
            window_found=True,
            window_title=target.title,
            action_taken=True,
            step_sent=prompt,
            message=f"{resolution.summary()} 다음 단계 {runtime.next_step_index}개째를 수동 전송했습니다.",
            target_reason=resolution.reason_text,
            target_score=resolution.score,
            lock_status=resolution.lock_status,
        )

    def build_step_prompt(self, session: SessionConfig, step_index: int) -> str:
        steps = session.project.steps()
        step = steps[step_index]
        total = len(steps)
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
                session.project.operator_rules or "",
            ]
        )

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
