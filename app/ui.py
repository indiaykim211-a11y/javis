from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from tkinter import BooleanVar, END, LEFT, StringVar, Tk, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from app.automation.windows_ui import WindowRect, WindowResolution, WindowsDesktopBridge
from app.models import RuntimeState, SessionConfig
from app.services.workflow import AutomationEngine
from app.state import SessionStore


class CodexPilotApp:
    def __init__(self, root: Tk, workspace: Path) -> None:
        self.root = root
        self.root.title("Codex Pilot")
        self.root.geometry("1280x940")

        self.store = SessionStore(workspace)
        self.session = self.store.load()
        self.runtime = RuntimeState()
        self.bridge = WindowsDesktopBridge()
        self.engine = AutomationEngine(self.bridge, self.store.capture_dir)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.stop_event = threading.Event()
        self.auto_thread: threading.Thread | None = None
        self._needs_refresh = False
        self._needs_session_save = False
        self._calibration_after_id: str | None = None

        self._build_layout()
        self._load_session()
        self._refresh_calibration_summary()
        self._refresh_runtime_labels()
        self._pump_logs()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=2)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=1)

        button_bar = ttk.Frame(self.root, padding=12)
        button_bar.grid(row=0, column=0, columnspan=2, sticky="ew")

        buttons = [
            ("세션 저장", self.save_session),
            ("창 새로고침", self.refresh_windows),
            ("Codex 포커스", self.focus_codex),
            ("즉시 캡처", self.capture_now),
            ("접근성 확인", self.inspect_accessibility),
            ("한 사이클 실행", self.run_cycle_once),
            ("다음 단계 보내기", self.send_next_step),
            ("자동 루프 시작/중지", self.toggle_auto),
        ]
        for label, command in buttons:
            ttk.Button(button_bar, text=label, command=command).pack(side=LEFT, padx=(0, 8))

        left = ttk.Frame(self.root, padding=(12, 0, 8, 12))
        left.grid(row=1, column=0, rowspan=2, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        left.rowconfigure(3, weight=1)

        project_frame = ttk.LabelFrame(left, text="프로젝트 컨텍스트", padding=12)
        project_frame.grid(row=0, column=0, sticky="nsew")
        project_frame.columnconfigure(0, weight=1)

        ttk.Label(project_frame, text="프로젝트 요약").grid(row=0, column=0, sticky="w")
        self.project_summary = ScrolledText(project_frame, height=4, wrap="word")
        self.project_summary.grid(row=1, column=0, sticky="ew", pady=(4, 8))

        ttk.Label(project_frame, text="목표 수준").grid(row=2, column=0, sticky="w")
        self.target_outcome = ScrolledText(project_frame, height=4, wrap="word")
        self.target_outcome.grid(row=3, column=0, sticky="ew", pady=(4, 8))

        ttk.Label(project_frame, text="운영 규칙").grid(row=4, column=0, sticky="w")
        self.operator_rules = ScrolledText(project_frame, height=6, wrap="word")
        self.operator_rules.grid(row=5, column=0, sticky="ew")

        steps_frame = ttk.LabelFrame(left, text="단계 목록 (한 줄에 한 단계)", padding=12)
        steps_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        steps_frame.columnconfigure(0, weight=1)
        steps_frame.rowconfigure(0, weight=1)

        self.steps_text = ScrolledText(steps_frame, wrap="word")
        self.steps_text.grid(row=0, column=0, sticky="nsew")

        log_frame = ttk.LabelFrame(left, text="로그", padding=12)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = ScrolledText(log_frame, height=12, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")

        right = ttk.Frame(self.root, padding=(8, 0, 12, 12))
        right.grid(row=1, column=1, rowspan=2, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)

        settings = ttk.LabelFrame(right, text="자동화 설정", padding=12)
        settings.grid(row=0, column=0, sticky="ew")
        settings.columnconfigure(1, weight=1)

        self.window_title_var = self._add_entry(settings, 0, "창 제목 포함")
        self.process_name_var = self._add_entry(settings, 1, "프로세스 이름")
        self.poll_interval_var = self._add_entry(settings, 2, "폴링 간격(초)")
        self.stable_cycles_var = self._add_entry(settings, 3, "안정화 필요 횟수")
        self.cooldown_var = self._add_entry(settings, 4, "전송 쿨다운(초)")
        self.threshold_var = self._add_entry(settings, 5, "시그니처 임계치")
        self.calibration_delay_var = self._add_entry(settings, 6, "캘리브레이션 대기(초)")
        self.click_x_var = self._add_entry(settings, 7, "입력창 상대 X")
        self.click_y_var = self._add_entry(settings, 8, "입력창 상대 Y")
        self.submit_var = self._add_check(settings, 9, "전송 후 Enter")
        self.dry_run_var = self._add_check(settings, 10, "DRY RUN")

        calibration = ttk.LabelFrame(right, text="입력창 캘리브레이션", padding=12)
        calibration.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        calibration.columnconfigure(0, weight=1)
        calibration.columnconfigure(1, weight=1)

        ttk.Label(
            calibration,
            text="딜레이 캡처를 누른 뒤 Codex 입력창 위에 마우스를 올려두면 현재 위치를 저장합니다.",
            wraplength=460,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        self.calibration_summary_var = StringVar(value="저장된 좌표가 없습니다.")
        self.calibration_status_var = StringVar(value="캘리브레이션 대기")

        ttk.Label(
            calibration,
            textvariable=self.calibration_summary_var,
            wraplength=460,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(
            calibration,
            textvariable=self.calibration_status_var,
            wraplength=460,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 8))

        ttk.Button(calibration, text="딜레이 캡처 시작", command=self.start_calibration_capture).grid(
            row=3, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(calibration, text="캡처 취소", command=self.cancel_calibration_capture).grid(
            row=3, column=1, sticky="ew"
        )
        ttk.Button(calibration, text="저장 위치 클릭", command=self.click_calibration_point).grid(
            row=4, column=0, sticky="ew", padx=(0, 6), pady=(8, 0)
        )
        ttk.Button(calibration, text="안전 테스트 입력", command=self.run_calibration_text_test).grid(
            row=4, column=1, sticky="ew", pady=(8, 0)
        )

        status = ttk.LabelFrame(right, text="실행 상태", padding=12)
        status.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        status.columnconfigure(0, weight=1)

        self.next_step_label = ttk.Label(status, text="다음 단계 인덱스: 0")
        self.next_step_label.grid(row=0, column=0, sticky="w")
        self.last_capture_label = ttk.Label(status, text="마지막 캡처: 없음", wraplength=460, justify="left")
        self.last_capture_label.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.auto_label = ttk.Label(status, text="자동 루프: 중지")
        self.auto_label.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.target_window_label = ttk.Label(status, text="타겟 창: 없음", wraplength=460, justify="left")
        self.target_window_label.grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.target_status_label = ttk.Label(status, text="타겟 상태: 타겟 없음", wraplength=460, justify="left")
        self.target_status_label.grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.target_reason_label = ttk.Label(status, text="선택 근거: 없음", wraplength=460, justify="left")
        self.target_reason_label.grid(row=5, column=0, sticky="w", pady=(8, 0))

        windows_frame = ttk.LabelFrame(right, text="현재 열린 창 / 선택 후보", padding=12)
        windows_frame.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        windows_frame.columnconfigure(0, weight=1)
        windows_frame.rowconfigure(0, weight=1)

        self.windows_list = ScrolledText(windows_frame, height=18, wrap="none")
        self.windows_list.grid(row=0, column=0, sticky="nsew")

    def _add_entry(self, parent: ttk.LabelFrame, row: int, label: str) -> StringVar:
        var = StringVar()
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(0, 6), padx=(0, 12))
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=(0, 6))
        return var

    def _add_check(self, parent: ttk.LabelFrame, row: int, label: str) -> BooleanVar:
        var = BooleanVar(value=False)
        ttk.Checkbutton(parent, text=label, variable=var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        return var

    def _load_session(self) -> None:
        self.project_summary.insert("1.0", self.session.project.project_summary)
        self.target_outcome.insert("1.0", self.session.project.target_outcome)
        self.operator_rules.insert("1.0", self.session.project.operator_rules)
        self.steps_text.insert("1.0", self.session.project.steps_text)

        self.window_title_var.set(self.session.window.title_contains)
        self.process_name_var.set(self.session.window.process_name)
        self.poll_interval_var.set(str(self.session.automation.poll_interval_sec))
        self.stable_cycles_var.set(str(self.session.automation.stable_cycles_required))
        self.cooldown_var.set(str(self.session.automation.min_seconds_between_actions))
        self.threshold_var.set(str(self.session.automation.signature_threshold))
        self.calibration_delay_var.set(str(self.session.automation.calibration_delay_sec))
        self.click_x_var.set(str(self.session.automation.input_click_x))
        self.click_y_var.set(str(self.session.automation.input_click_y))
        self.submit_var.set(self.session.automation.submit_with_enter)
        self.dry_run_var.set(self.session.automation.dry_run)

        if self.session.window.last_title:
            self.runtime.last_target_title = self.session.window.last_title
        if self.session.window.last_reason:
            self.runtime.last_target_reason = self.session.window.last_reason
            self.runtime.last_target_score = self.session.window.last_score
            self.runtime.target_lock_status = "저장된 잠금 창"

    def _collect_session(self) -> SessionConfig:
        session = SessionConfig.from_dict(self.session.to_dict())
        session.project.project_summary = self.project_summary.get("1.0", END).strip()
        session.project.target_outcome = self.target_outcome.get("1.0", END).strip()
        session.project.operator_rules = self.operator_rules.get("1.0", END).strip()
        session.project.steps_text = self.steps_text.get("1.0", END).strip()

        session.window.title_contains = self.window_title_var.get().strip()
        session.window.process_name = self.process_name_var.get().strip()
        session.automation.poll_interval_sec = int(self.poll_interval_var.get().strip() or "8")
        session.automation.stable_cycles_required = int(self.stable_cycles_var.get().strip() or "3")
        session.automation.min_seconds_between_actions = int(self.cooldown_var.get().strip() or "45")
        session.automation.signature_threshold = float(self.threshold_var.get().strip() or "0.018")
        session.automation.calibration_delay_sec = int(self.calibration_delay_var.get().strip() or "3")
        session.automation.input_click_x = int(self.click_x_var.get().strip() or "350")
        session.automation.input_click_y = int(self.click_y_var.get().strip() or "760")
        session.automation.submit_with_enter = bool(self.submit_var.get())
        session.automation.dry_run = bool(self.dry_run_var.get())
        return session

    def _save_session_quietly(self) -> None:
        self.store.save(self.session)

    def save_session(self) -> None:
        try:
            self.session = self._collect_session()
            self._save_session_quietly()
            self._refresh_calibration_summary()
            self._log("세션 설정을 저장했습니다.")
        except Exception as exc:
            messagebox.showerror("저장 실패", str(exc))

    def refresh_windows(self) -> None:
        try:
            self.session = self._collect_session()
            resolution = self.bridge.resolve_target(self.session.window)
            windows = self.bridge.list_windows()
            self._sync_runtime_from_resolution(resolution)
        except Exception as exc:
            messagebox.showerror("창 조회 실패", str(exc))
            return

        lines = ["선택 결과", resolution.summary(), ""]
        lines.append("후보 점수")
        if resolution.candidates:
            selected_handle = resolution.selected.handle if resolution.selected else None
            for candidate in resolution.candidates[:10]:
                lines.append(candidate.format_line(selected_handle=selected_handle))
        else:
            lines.append("조건에 맞는 후보가 없습니다.")

        lines.extend(["", "전체 열린 창"])
        for item in windows:
            lines.append(
                f"  {item.process_name:<14} | PID {item.process_id:<6} | HWND {item.handle:<8} | {item.title}"
            )

        self.windows_list.delete("1.0", END)
        self.windows_list.insert("1.0", "\n".join(lines))
        self._refresh_runtime_labels()
        self._log(f"창 {len(windows)}개를 불러왔습니다. {resolution.summary()}")

    def _resolve_codex_target(self) -> WindowResolution:
        self.session = self._collect_session()
        resolution = self.bridge.resolve_target(self.session.window)
        self._sync_runtime_from_resolution(resolution)
        if resolution.selected is None:
            raise RuntimeError(resolution.summary())
        return resolution

    def _remember_resolution(self, resolution: WindowResolution) -> None:
        if resolution.selected is None:
            return
        self.session.window.remember_success(
            handle=resolution.selected.handle,
            process_id=resolution.selected.process_id,
            title=resolution.selected.title,
            process_name=resolution.selected.process_name,
            score=resolution.score,
            reason=resolution.reason_text or resolution.summary(),
        )
        self._save_session_quietly()

    def _sync_runtime_from_resolution(self, resolution: WindowResolution) -> None:
        self.runtime.last_target_title = resolution.selected.title if resolution.selected else ""
        self.runtime.last_target_reason = resolution.reason_text or resolution.summary()
        self.runtime.last_target_score = resolution.score if resolution.selected else None
        self.runtime.target_lock_status = resolution.lock_status

    def focus_codex(self) -> None:
        try:
            resolution = self._resolve_codex_target()
            self.bridge.focus_window(resolution.selected.handle)
            self._remember_resolution(resolution)
            self._refresh_runtime_labels()
            self._log(f"Codex 창을 포커스했습니다. {resolution.summary()}")
        except Exception as exc:
            messagebox.showerror("포커스 실패", str(exc))

    def capture_now(self) -> None:
        try:
            resolution = self._resolve_codex_target()
            stamp = int(time.time())
            path = self.store.capture_dir / f"manual-{stamp}.bmp"
            self.bridge.capture_window(resolution.selected.handle, path)
            self.runtime.last_capture_path = str(path)
            self._remember_resolution(resolution)
            self._refresh_runtime_labels()
            self._log(f"Codex 창을 캡처했습니다. {resolution.summary()} | 캡처: {path}")
        except Exception as exc:
            messagebox.showerror("캡처 실패", str(exc))

    def inspect_accessibility(self) -> None:
        try:
            resolution = self._resolve_codex_target()
            items = self.bridge.inspect_automation_tree(resolution.selected.title, limit=40)
            self._remember_resolution(resolution)
            if not items:
                self._log(f"{resolution.summary()} 접근성 트리에서 읽을 수 있는 항목이 거의 없었습니다.")
                return
            summary = "\n".join(
                f"{item.get('type', '')} | {item.get('name', '')} | {item.get('automationId', '')}"
                for item in items
            )
            self._log(f"{resolution.summary()} 접근성 트리 일부:\n{summary}")
        except Exception as exc:
            messagebox.showerror("접근성 확인 실패", str(exc))

    def start_calibration_capture(self) -> None:
        if self._calibration_after_id is not None:
            self.calibration_status_var.set("이미 딜레이 캡처가 진행 중입니다.")
            return

        try:
            resolution = self._resolve_codex_target()
            delay = int(self.calibration_delay_var.get().strip() or "3")
            if delay < 1 or delay > 15:
                raise ValueError("캘리브레이션 대기 시간은 1초에서 15초 사이로 설정해 주세요.")
            self.session.automation.calibration_delay_sec = delay
            self._remember_resolution(resolution)
            self.bridge.focus_window(resolution.selected.handle)
            self._refresh_runtime_labels()
            self._refresh_calibration_summary()
            self.calibration_status_var.set(
                f"{delay}초 안에 Codex 입력창 위에 마우스를 올려두세요. 시간이 끝나면 현재 위치를 저장합니다."
            )
            self._log(f"캘리브레이션을 시작했습니다. {delay}초 뒤 현재 마우스 위치를 저장합니다.")
            self._run_calibration_countdown(resolution, delay)
        except Exception as exc:
            messagebox.showerror("캘리브레이션 시작 실패", str(exc))

    def _run_calibration_countdown(self, resolution: WindowResolution, remaining: int) -> None:
        if remaining <= 0:
            self._calibration_after_id = None
            self._finish_calibration_capture(resolution)
            return

        self.calibration_status_var.set(
            f"{remaining}초 후 현재 마우스 위치를 저장합니다. Codex 입력창 위에 마우스를 올려두세요."
        )
        self._calibration_after_id = self.root.after(
            1000,
            lambda: self._run_calibration_countdown(resolution, remaining - 1),
        )

    def cancel_calibration_capture(self) -> None:
        if self._calibration_after_id is None:
            self.calibration_status_var.set("진행 중인 딜레이 캡처가 없습니다.")
            return
        self.root.after_cancel(self._calibration_after_id)
        self._calibration_after_id = None
        self.calibration_status_var.set("딜레이 캡처를 취소했습니다.")
        self._log("딜레이 캡처를 취소했습니다.")

    def _finish_calibration_capture(self, resolution: WindowResolution) -> None:
        try:
            rect = self.bridge.get_window_rect(resolution.selected.handle)
            cursor_x, cursor_y = self.bridge.get_cursor_position()
            if rect.width <= 0 or rect.height <= 0:
                raise RuntimeError("Codex 창 크기를 읽지 못했습니다.")
            if not rect.contains(cursor_x, cursor_y):
                raise RuntimeError("마우스가 Codex 창 영역 밖에 있어 좌표를 저장하지 못했습니다.")

            offset_x, offset_y = rect.to_relative(cursor_x, cursor_y)
            self.session.automation.remember_calibration(
                offset_x=offset_x,
                offset_y=offset_y,
                window_width=rect.width,
                window_height=rect.height,
            )
            self.click_x_var.set(str(offset_x))
            self.click_y_var.set(str(offset_y))
            self.calibration_delay_var.set(str(self.session.automation.calibration_delay_sec))
            self._save_session_quietly()
            self._refresh_calibration_summary()
            self.calibration_status_var.set(
                f"저장 완료: ({offset_x}, {offset_y}) @ {rect.width}x{rect.height}"
            )
            self._log(
                "캘리브레이션 좌표를 저장했습니다. "
                f"상대 좌표 ({offset_x}, {offset_y}), 기준 창 크기 {rect.width}x{rect.height}"
            )
        except Exception as exc:
            self.calibration_status_var.set(f"캘리브레이션 실패: {exc}")
            self._log(f"캘리브레이션 실패: {exc}")

    def click_calibration_point(self) -> None:
        try:
            resolution = self._resolve_codex_target()
            click_x, click_y, rect = self._resolve_scaled_click(resolution.selected.handle)
            self.bridge.click_in_window(resolution.selected.handle, click_x, click_y)
            self._remember_resolution(resolution)
            self.calibration_status_var.set(
                f"저장 위치 클릭 완료: ({click_x}, {click_y}) @ 현재 창 {rect.width}x{rect.height}"
            )
            self._refresh_runtime_labels()
            self._log(
                "저장된 입력 위치를 클릭했습니다. "
                f"적용 좌표 ({click_x}, {click_y}), 현재 창 크기 {rect.width}x{rect.height}"
            )
        except Exception as exc:
            messagebox.showerror("저장 위치 클릭 실패", str(exc))

    def run_calibration_text_test(self) -> None:
        try:
            resolution = self._resolve_codex_target()
            click_x, click_y, rect = self._resolve_scaled_click(resolution.selected.handle)
            test_text = self.session.automation.calibration_test_text
            self.bridge.send_text(
                resolution.selected.handle,
                test_text,
                click_x=click_x,
                click_y=click_y,
                submit=False,
            )
            self._remember_resolution(resolution)
            self.calibration_status_var.set(
                "안전 테스트 입력 완료: 메시지를 입력창에 붙여넣었지만 전송하지 않았습니다."
            )
            self._refresh_runtime_labels()
            self._log(
                "안전 테스트 입력을 수행했습니다. "
                f"적용 좌표 ({click_x}, {click_y}), 현재 창 크기 {rect.width}x{rect.height}"
            )
        except Exception as exc:
            messagebox.showerror("안전 테스트 입력 실패", str(exc))

    def _resolve_scaled_click(self, handle: int) -> tuple[int, int, WindowRect]:
        rect = self.bridge.get_window_rect(handle)
        click_x, click_y = self.session.automation.resolve_click_offset(
            actual_width=rect.width,
            actual_height=rect.height,
        )
        return click_x, click_y, rect

    def run_cycle_once(self) -> None:
        try:
            self.session = self._collect_session()
            report = self.engine.run_cycle(self.session, self.runtime)
            self._apply_report(report)
        except Exception as exc:
            messagebox.showerror("사이클 실행 실패", str(exc))

    def send_next_step(self) -> None:
        try:
            self.session = self._collect_session()
            report = self.engine.send_next_step_now(self.session, self.runtime)
            self._apply_report(report)
        except Exception as exc:
            messagebox.showerror("전송 실패", str(exc))

    def toggle_auto(self) -> None:
        if self.runtime.auto_running:
            self.stop_event.set()
            self.runtime.auto_running = False
            self._refresh_runtime_labels()
            self._log("자동 루프를 중지했습니다.")
            return

        try:
            self.session = self._collect_session()
            self._save_session_quietly()
            self._refresh_calibration_summary()
        except Exception as exc:
            messagebox.showerror("설정 오류", str(exc))
            return

        self.stop_event.clear()
        self.runtime.auto_running = True
        self._refresh_runtime_labels()
        self.auto_thread = threading.Thread(target=self._auto_loop_worker, daemon=True)
        self.auto_thread.start()
        self._log("자동 루프를 시작했습니다.")

    def _auto_loop_worker(self) -> None:
        while not self.stop_event.is_set():
            try:
                report = self.engine.run_cycle(self.session, self.runtime)
                self.log_queue.put(self._format_report(report))
                self._needs_refresh = True
                self._needs_session_save = True
            except Exception as exc:
                self.log_queue.put(f"[오류] 자동 루프 실패: {exc}")
            wait_seconds = max(self.session.automation.poll_interval_sec, 1)
            for _ in range(wait_seconds * 10):
                if self.stop_event.is_set():
                    break
                time.sleep(0.1)

    def _apply_report(self, report) -> None:
        self._save_session_quietly()
        self._log(self._format_report(report))
        self._refresh_runtime_labels()

    def _format_report(self, report) -> str:
        parts = [report.message]
        if report.window_title:
            parts.append(f"창: {report.window_title}")
        if report.lock_status:
            parts.append(f"타겟 상태: {report.lock_status}")
        if report.target_score is not None:
            parts.append(f"타겟 점수: {report.target_score}")
        if report.target_reason:
            parts.append(f"선택 근거: {report.target_reason}")
        if report.capture_path:
            parts.append(f"캡처: {report.capture_path}")
        if report.signature_distance is not None:
            parts.append(f"시그니처 거리: {report.signature_distance:.4f}")
        if report.step_sent:
            preview = report.step_sent.replace("\n", " ")[:160]
            parts.append(f"프롬프트: {preview}")
        return " | ".join(parts)

    def _refresh_calibration_summary(self) -> None:
        summary = self.session.automation.calibration_summary()
        delay = self.session.automation.calibration_delay_sec
        self.calibration_summary_var.set(f"{summary} | 딜레이 캡처 {delay}초")

    def _refresh_runtime_labels(self) -> None:
        score_text = "없음" if self.runtime.last_target_score is None else str(self.runtime.last_target_score)
        self.next_step_label.config(text=f"다음 단계 인덱스: {self.runtime.next_step_index}")
        self.last_capture_label.config(text=f"마지막 캡처: {self.runtime.last_capture_path or '없음'}")
        self.auto_label.config(text=f"자동 루프: {'실행 중' if self.runtime.auto_running else '중지'}")
        self.target_window_label.config(text=f"타겟 창: {self.runtime.last_target_title or '없음'}")
        self.target_status_label.config(
            text=f"타겟 상태: {self.runtime.target_lock_status or '타겟 없음'} | 점수: {score_text}"
        )
        self.target_reason_label.config(text=f"선택 근거: {self.runtime.last_target_reason or '없음'}")

    def _pump_logs(self) -> None:
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._log(line)
        if self._needs_session_save:
            self._save_session_quietly()
            self._needs_session_save = False
        if self._needs_refresh:
            self._refresh_runtime_labels()
            self._needs_refresh = False
        self.root.after(250, self._pump_logs)

    def _log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert(END, message.strip() + "\n")
        self.log_text.see(END)
        self.log_text.configure(state="disabled")


def launch_app() -> None:
    workspace = Path(__file__).resolve().parents[1]
    root = Tk()
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    CodexPilotApp(root, workspace)
    root.mainloop()
