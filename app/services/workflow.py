from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from app.automation.bmp import compute_signature, normalized_distance
from app.automation.windows_ui import WindowResolution, WindowsDesktopBridge
from app.models import (
    CodexAutomationModeDecision,
    CycleReport,
    PopupActionModel,
    PromptPreview,
    RuntimeState,
    SessionConfig,
    SurfaceStateModel,
    StepQueueItem,
    get_codex_automation_mode_option,
    get_codex_automation_preset,
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
                    PopupActionModel("show_summary", "요약", True),
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
                    PopupActionModel("show_summary", "요약", True),
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
                    PopupActionModel("show_summary", "요약", True),
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
                PopupActionModel("show_summary", "요약", True),
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
