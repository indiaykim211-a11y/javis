from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from tkinter import BooleanVar, END, LEFT, StringVar, TclError, Tk, Toplevel, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from app.automation.windows_ui import WindowRect, WindowResolution, WindowsDesktopBridge
from app.models import (
    CODEX_AUTOMATION_MODE_OPTIONS,
    CODEX_AUTOMATION_PRESETS,
    POLICY_SECTION_SPECS,
    PersistedSessionState,
    PromptPreview,
    RuntimeState,
    SessionConfig,
    StepQueueItem,
    SurfaceStateModel,
    get_codex_automation_mode_option,
)
from app.services.workflow import AutomationEngine
from app.state import SessionStore


class JavisApp:
    def __init__(self, root: Tk, workspace: Path) -> None:
        self.root = root
        self.root.title("javis")
        self._popup_expanded_size = (432, 388)
        self._popup_compact_size = (388, 248)
        self.root.geometry(f"{self._popup_expanded_size[0]}x{self._popup_expanded_size[1]}")
        self.root.minsize(360, 230)
        self.root.protocol("WM_DELETE_WINDOW", self._close_application)
        try:
            self.root.attributes("-topmost", True)
        except TclError:
            pass

        self.store = SessionStore(workspace)
        persisted = self.store.load()
        self.session = persisted.session
        self.runtime = persisted.runtime
        self.recent_projects = persisted.recent_projects
        self.session_schema_version = persisted.schema_version
        self.last_saved_at = persisted.saved_at
        self.log_reference_path = persisted.log_path or str(self.store.log_path)
        self.bridge = WindowsDesktopBridge()
        self.engine = AutomationEngine(self.bridge, self.store.capture_dir)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.stop_event = threading.Event()
        self.auto_thread: threading.Thread | None = None
        self._needs_refresh = False
        self._needs_prompt_refresh = False
        self._needs_session_save = False
        self._calibration_after_id: str | None = None
        self._suspend_prompt_modified = False
        self._popup_compact = False
        self._current_preview = PromptPreview()
        self._current_queue: list[StepQueueItem] = []
        self._surface_state = SurfaceStateModel()
        self._current_codex_strategy_prompt = ""
        self._current_codex_strategy_runbook = ""
        self._current_automation_runboard = ""
        self._current_triage_bridge = ""
        self._current_native_fallback_matrix = ""

        self._build_styles()
        self._build_popup_shell()
        self._build_control_center()
        self.control_center.withdraw()

        self._load_session()
        self._refresh_calibration_summary()
        self._refresh_persistence_panel()
        self._refresh_prompt_panel_from_current_session()
        self._refresh_runtime_labels()
        self._pump_logs()
        if self.last_saved_at:
            self._log(f"저장된 세션을 복원했습니다. 마지막 저장 시각은 {self.last_saved_at.replace('T', ' ')} 입니다.")

    def _build_styles(self) -> None:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("PopupShell.TFrame", padding=18)
        style.configure("PopupTitle.TLabel", font=("Segoe UI Semibold", 16))
        style.configure("PopupProject.TLabel", font=("Segoe UI", 9))
        style.configure("PopupBadge.TLabel", font=("Segoe UI Semibold", 9))
        style.configure("PopupHeadline.TLabel", font=("Segoe UI Semibold", 13))
        style.configure("PopupBody.TLabel", font=("Segoe UI", 10))
        style.configure("PopupMeta.TLabel", font=("Segoe UI", 9))
        style.configure("PopupSection.TLabel", font=("Segoe UI Semibold", 9))
        style.configure("PopupPrimary.TButton", padding=(10, 8))
        style.configure("PopupSecondary.TButton", padding=(10, 8))

    def _build_popup_shell(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        shell = ttk.Frame(self.root, style="PopupShell.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)
        self.popup_shell = shell

        self.popup_title_var = StringVar(value="대기 중")
        self.popup_project_var = StringVar(value="아직 불러온 프로젝트가 없습니다.")
        self.popup_badge_var = StringVar(value="준비")
        self.popup_status_var = StringVar(value="프로젝트를 불러오면 현재 상태를 여기서 바로 안내해드립니다.")
        self.popup_reason_var = StringVar(value="Control Center에서 프로젝트와 단계 목록을 먼저 확인해 주세요.")
        self.popup_next_action_var = StringVar(value="설정을 열어서 Codex 대상과 단계 계획을 정리하면 바로 이어갈 수 있습니다.")
        self.popup_compact_hint_var = StringVar(value="지금 해야 할 일은 아직 없습니다.")
        self.popup_meta_var = StringVar(value="진행 0/0")
        self.popup_detail_var = StringVar(value="타깃 점수 없음 | 안정 카운트 0 | 최근 캡처 없음")
        self.popup_risk_var = StringVar(value="위험 레벨 낮음")
        self.popup_last_event_var = StringVar(value="최근 이벤트가 아직 없습니다.")
        self.compact_button_var = StringVar(value="간단히")

        header = ttk.Frame(shell)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title_block = ttk.Frame(header)
        title_block.grid(row=0, column=0, sticky="w")
        ttk.Label(title_block, text="javis", style="PopupTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.popup_project_label = ttk.Label(title_block, textvariable=self.popup_project_var, style="PopupProject.TLabel")
        self.popup_project_label.grid(
            row=1, column=0, sticky="w", pady=(2, 0)
        )

        header_actions = ttk.Frame(header)
        header_actions.grid(row=0, column=1, sticky="e")
        ttk.Label(header_actions, textvariable=self.popup_badge_var, style="PopupBadge.TLabel").pack(
            side=LEFT, padx=(0, 8)
        )
        ttk.Button(header_actions, text="설정", command=self.open_control_center).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            header_actions,
            textvariable=self.compact_button_var,
            command=self.toggle_popup_compact,
        ).pack(side=LEFT)

        ttk.Separator(shell).grid(row=1, column=0, sticky="ew", pady=10)

        body = ttk.Frame(shell)
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        self.popup_body = body

        status_card = ttk.LabelFrame(body, text="지금 상태", padding=12)
        status_card.grid(row=0, column=0, sticky="ew")
        status_card.columnconfigure(0, weight=1)
        ttk.Label(status_card, textvariable=self.popup_title_var, style="PopupHeadline.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.popup_status_label = ttk.Label(
            status_card,
            textvariable=self.popup_status_var,
            style="PopupBody.TLabel",
            wraplength=340,
            justify="left",
        )
        self.popup_status_label.grid(row=1, column=0, sticky="w", pady=(6, 0))

        self.popup_compact_frame = ttk.LabelFrame(body, text="한눈에 보기", padding=12)
        self.popup_compact_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.popup_compact_frame.columnconfigure(0, weight=1)
        self.popup_compact_hint_label = ttk.Label(
            self.popup_compact_frame,
            textvariable=self.popup_compact_hint_var,
            style="PopupBody.TLabel",
            wraplength=340,
            justify="left",
        )
        self.popup_compact_hint_label.grid(row=0, column=0, sticky="w")
        self.popup_compact_frame.grid_remove()

        self.popup_detail_frame = ttk.Frame(body)
        self.popup_detail_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.popup_detail_frame.columnconfigure(0, weight=1)

        reason_card = ttk.LabelFrame(self.popup_detail_frame, text="판단 이유", padding=12)
        reason_card.grid(row=0, column=0, sticky="ew")
        reason_card.columnconfigure(0, weight=1)
        self.popup_reason_label = ttk.Label(
            reason_card,
            textvariable=self.popup_reason_var,
            style="PopupBody.TLabel",
            wraplength=340,
            justify="left",
        )
        self.popup_reason_label.grid(row=0, column=0, sticky="w")

        next_card = ttk.LabelFrame(self.popup_detail_frame, text="추천 행동", padding=12)
        next_card.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        next_card.columnconfigure(0, weight=1)
        self.popup_next_label = ttk.Label(
            next_card,
            textvariable=self.popup_next_action_var,
            style="PopupBody.TLabel",
            wraplength=340,
            justify="left",
        )
        self.popup_next_label.grid(row=0, column=0, sticky="w")

        footer = ttk.Frame(body)
        footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=1)
        self.popup_meta_label = ttk.Label(footer, textvariable=self.popup_meta_var, style="PopupMeta.TLabel")
        self.popup_meta_label.grid(row=0, column=0, sticky="w")
        self.popup_risk_label = ttk.Label(footer, textvariable=self.popup_risk_var, style="PopupMeta.TLabel")
        self.popup_risk_label.grid(row=0, column=1, sticky="e")
        self.popup_detail_label = ttk.Label(
            footer,
            textvariable=self.popup_detail_var,
            style="PopupMeta.TLabel",
            wraplength=340,
            justify="left",
        )
        self.popup_detail_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.popup_last_event_label = ttk.Label(
            footer,
            textvariable=self.popup_last_event_var,
            style="PopupMeta.TLabel",
            wraplength=340,
            justify="left",
        )
        self.popup_last_event_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.popup_footer_frame = footer

        action_bar = ttk.Frame(shell)
        action_bar.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        self.popup_action_bar = action_bar
        for column in range(4):
            action_bar.columnconfigure(column, weight=1)
        for row in range(2):
            action_bar.rowconfigure(row, weight=1)

        self.popup_action_buttons: list[ttk.Button] = []
        for column in range(4):
            button = ttk.Button(action_bar, text="", style="PopupSecondary.TButton")
            button.grid(row=0, column=column, sticky="ew", padx=(0, 6) if column < 3 else 0)
            self.popup_action_buttons.append(button)

        self.root.bind("<Configure>", self._on_popup_configure)

    def _build_control_center(self) -> None:
        self.control_center = Toplevel(self.root)
        self.control_center.title("javis Control Center")
        self.control_center.geometry("1280x940")
        self.control_center.transient(self.root)
        self.control_center.protocol("WM_DELETE_WINDOW", self.hide_control_center)
        self._build_control_center_layout(self.control_center)

    def _build_control_center_layout(self, parent: Toplevel) -> None:
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(1, weight=1)

        self.control_header_project_var = StringVar(value="프로젝트 정보 미입력")
        self.control_header_status_var = StringVar(value="세션 상태를 불러오는 중입니다.")
        self.control_section_var = StringVar(value="project")
        self.control_section_frames: dict[str, ttk.Frame] = {}
        self.control_section_labels: dict[str, str] = {}
        self.control_nav_buttons: dict[str, ttk.Button] = {}
        self.codex_strategy_choice_by_label: dict[str, str] = {}
        self.codex_strategy_label_by_id: dict[str, str] = {}
        self.codex_mode_choice_by_label: dict[str, str] = {}
        self.codex_mode_label_by_id: dict[str, str] = {}

        header = ttk.Frame(parent, padding=12)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.columnconfigure(0, weight=1)

        title_block = ttk.Frame(header)
        title_block.grid(row=0, column=0, sticky="w")
        ttk.Label(title_block, text="Control Center", style="PopupTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            title_block,
            textvariable=self.control_header_project_var,
            style="PopupProject.TLabel",
            wraplength=720,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Label(
            title_block,
            textvariable=self.control_header_status_var,
            wraplength=720,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))

        header_actions = ttk.Frame(header)
        header_actions.grid(row=0, column=1, sticky="e")
        ttk.Button(header_actions, text="세션 저장", command=self.save_session).pack(side=LEFT, padx=(0, 8))
        ttk.Button(header_actions, text="팝업으로", command=self.hide_control_center).pack(side=LEFT, padx=(0, 8))
        ttk.Button(header_actions, text="닫기", command=self.hide_control_center).pack(side=LEFT)

        body = ttk.Frame(parent, padding=(12, 0, 12, 12))
        body.grid(row=1, column=0, columnspan=2, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        nav = ttk.LabelFrame(body, text="섹션", padding=12)
        nav.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        self.control_nav = nav

        content = ttk.Frame(body)
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)
        self.control_content = content

        project_section = self._create_control_section("project", "프로젝트")
        codex_strategy_section = self._create_control_section("codex_strategy", "Codex 전략")
        policy_section = self._create_control_section("policy", "정책")
        codex_section = self._create_control_section("codex", "Codex 제어")
        evidence_section = self._create_control_section("evidence", "증거 / 로그")
        safety_section = self._create_control_section("safety", "안전 / 자동화")
        model_voice_section = self._create_control_section("model_voice", "모델 / 음성")
        advanced_section = self._create_control_section("advanced", "고급")

        project_section.columnconfigure(0, weight=1)
        project_section.rowconfigure(2, weight=1)

        self.schema_version_var = StringVar(value="세션 스키마 v1")
        self.last_saved_var = StringVar(value="마지막 저장: 없음")
        self.log_reference_var = StringVar(value="로그 파일: 없음")
        self.recent_project_var = StringVar(value="")
        self.project_home_title_var = StringVar(value="프로젝트 정보 미입력")
        self.project_home_target_var = StringVar(value="목표 수준이 아직 없습니다.")
        self.project_home_strategy_var = StringVar(value="운영 프로필: 아직 선택된 Codex 전략이 없습니다.")
        self.project_home_progress_var = StringVar(value="현재 단계 정보가 없습니다.")
        self.project_home_status_var = StringVar(value="마지막 상태 정보가 아직 없습니다.")
        self.project_home_capture_var = StringVar(value="최근 캡처 없음")
        self.recent_project_summary_var = StringVar(value="최근 프로젝트가 없습니다.")
        self.recent_project_target_var = StringVar(value="불러올 항목을 선택하면 목표와 진행 상태를 보여드립니다.")
        self.recent_project_strategy_var = StringVar(value="운영 프로필 정보 없음")
        self.recent_project_progress_var = StringVar(value="진행 정보 없음")
        self.recent_project_capture_var = StringVar(value="최근 캡처 없음")
        self.policy_status_var = StringVar(value="정책 저장 상태: 변경 없음")
        self.policy_last_edited_var = StringVar(value="최근 수정: 없음")
        self.policy_template_mix_var = StringVar(value="커스텀 0 / 기본 6")
        self.policy_section_state_var = StringVar(value="현재 섹션: 운영 마스터 | 기본 템플릿")
        self.policy_note_var = StringVar(value="")
        self._policy_loading = False
        self._policy_dirty = False
        self._policy_live_edited_at = ""
        self._policy_last_edited_section = ""

        home_frame = ttk.Frame(project_section)
        home_frame.grid(row=0, column=0, sticky="ew")
        home_frame.columnconfigure(0, weight=1)
        home_frame.columnconfigure(1, weight=1)

        current_card = ttk.LabelFrame(home_frame, text="현재 프로젝트", padding=12)
        current_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        current_card.columnconfigure(0, weight=1)

        ttk.Label(current_card, textvariable=self.project_home_title_var, style="PopupHeadline.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            current_card,
            textvariable=self.project_home_target_var,
            wraplength=340,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(
            current_card,
            textvariable=self.project_home_strategy_var,
            wraplength=340,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            current_card,
            textvariable=self.project_home_progress_var,
            wraplength=340,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            current_card,
            textvariable=self.project_home_status_var,
            wraplength=340,
            justify="left",
        ).grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            current_card,
            textvariable=self.project_home_capture_var,
            wraplength=340,
            justify="left",
        ).grid(row=5, column=0, sticky="w", pady=(8, 0))
        ttk.Label(current_card, textvariable=self.schema_version_var, wraplength=340, justify="left").grid(
            row=6, column=0, sticky="w", pady=(12, 0)
        )
        ttk.Label(current_card, textvariable=self.last_saved_var, wraplength=340, justify="left").grid(
            row=7, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(current_card, textvariable=self.log_reference_var, wraplength=340, justify="left").grid(
            row=8, column=0, sticky="w", pady=(4, 0)
        )

        current_actions = ttk.Frame(current_card)
        current_actions.grid(row=9, column=0, sticky="ew", pady=(12, 0))
        current_actions.columnconfigure(0, weight=1)
        current_actions.columnconfigure(1, weight=1)
        current_actions.columnconfigure(2, weight=1)
        ttk.Button(current_actions, text="현재 프로젝트 저장", command=self.save_session).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(
            current_actions,
            text="Codex 전략으로 이동",
            command=lambda: self._select_control_center_section("codex_strategy"),
        ).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(
            current_actions,
            text="Codex 제어로 이동",
            command=lambda: self._select_control_center_section("codex"),
        ).grid(row=0, column=2, sticky="ew")

        recent_card = ttk.LabelFrame(home_frame, text="최근 프로젝트 / 이어가기", padding=12)
        recent_card.grid(row=0, column=1, sticky="nsew")
        recent_card.columnconfigure(0, weight=1)

        self.recent_projects_combo = ttk.Combobox(recent_card, textvariable=self.recent_project_var, state="readonly")
        self.recent_projects_combo.grid(row=0, column=0, sticky="ew")
        self.recent_projects_combo.bind("<<ComboboxSelected>>", self._on_recent_project_selected)

        ttk.Label(
            recent_card,
            textvariable=self.recent_project_summary_var,
            wraplength=340,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Label(
            recent_card,
            textvariable=self.recent_project_target_var,
            wraplength=340,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            recent_card,
            textvariable=self.recent_project_strategy_var,
            wraplength=340,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            recent_card,
            textvariable=self.recent_project_progress_var,
            wraplength=340,
            justify="left",
        ).grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            recent_card,
            textvariable=self.recent_project_capture_var,
            wraplength=340,
            justify="left",
        ).grid(row=5, column=0, sticky="w", pady=(8, 0))

        recent_actions = ttk.Frame(recent_card)
        recent_actions.grid(row=6, column=0, sticky="ew", pady=(12, 0))
        recent_actions.columnconfigure(0, weight=1)
        recent_actions.columnconfigure(1, weight=1)
        self.load_recent_button = ttk.Button(
            recent_actions,
            text="선택한 프로젝트 이어가기",
            command=self.load_recent_project_selection,
        )
        self.load_recent_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            recent_actions,
            text="프로젝트 섹션 새로고침",
            command=self._refresh_project_home,
        ).grid(row=0, column=1, sticky="ew")

        project_frame = ttk.LabelFrame(project_section, text="현재 프로젝트 편집", padding=12)
        project_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        project_frame.columnconfigure(0, weight=1)

        ttk.Label(project_frame, text="프로젝트 요약").grid(row=0, column=0, sticky="w")
        self.project_summary = ScrolledText(project_frame, height=4, wrap="word")
        self.project_summary.grid(row=1, column=0, sticky="ew", pady=(4, 8))

        ttk.Label(project_frame, text="목표 수준").grid(row=2, column=0, sticky="w")
        self.target_outcome = ScrolledText(project_frame, height=4, wrap="word")
        self.target_outcome.grid(row=3, column=0, sticky="ew")

        steps_frame = ttk.LabelFrame(project_section, text="단계 목록", padding=12)
        steps_frame.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        steps_frame.columnconfigure(0, weight=1)
        steps_frame.rowconfigure(0, weight=1)

        self.steps_text = ScrolledText(steps_frame, wrap="word")
        self.steps_text.grid(row=0, column=0, sticky="nsew")

        project_footer = ttk.Frame(project_section)
        project_footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        project_footer.columnconfigure(0, weight=1)
        project_footer.columnconfigure(1, weight=1)
        ttk.Button(
            project_footer,
            text="정책 섹션으로 이동",
            command=lambda: self._select_control_center_section("policy"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            project_footer,
            text="팝업으로 돌아가기",
            command=self.hide_control_center,
        ).grid(row=0, column=1, sticky="ew")

        codex_strategy_section.columnconfigure(0, weight=1)
        codex_strategy_section.rowconfigure(5, weight=1)

        strategy_intro = ttk.LabelFrame(codex_strategy_section, text="Codex-first 안내", padding=12)
        strategy_intro.grid(row=0, column=0, sticky="ew")
        strategy_intro.columnconfigure(0, weight=1)
        ttk.Label(
            strategy_intro,
            text=(
                "Phase 3에서는 무조건 automation으로 밀지 않고, 먼저 no automation / thread / project 중 "
                "무엇이 맞는지 고른 뒤 Codex 앱으로 자연스럽게 handoff합니다."
            ),
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        strategy_picker = ttk.LabelFrame(codex_strategy_section, text="운영 시나리오 선택", padding=12)
        strategy_picker.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        strategy_picker.columnconfigure(1, weight=1)

        self.codex_strategy_var = StringVar()
        for preset in CODEX_AUTOMATION_PRESETS:
            label = f"{preset.title} | {preset.automation_type}"
            self.codex_strategy_choice_by_label[label] = preset.preset_id
            self.codex_strategy_label_by_id[preset.preset_id] = label

        ttk.Label(strategy_picker, text="추천 프리셋").grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.codex_strategy_combo = ttk.Combobox(
            strategy_picker,
            textvariable=self.codex_strategy_var,
            state="readonly",
            values=list(self.codex_strategy_choice_by_label.keys()),
        )
        self.codex_strategy_combo.grid(row=0, column=1, sticky="ew")
        self.codex_strategy_combo.bind("<<ComboboxSelected>>", self._on_codex_strategy_selected)

        self.codex_strategy_status_var = StringVar(value="현재 프로젝트에 맞는 Codex 운영 프리셋을 고를 수 있습니다.")
        ttk.Label(
            strategy_picker,
            textvariable=self.codex_strategy_status_var,
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        strategy_actions = ttk.Frame(strategy_picker)
        strategy_actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        for index, (label, command) in enumerate(
            [
                ("프롬프트 새로고침", self.refresh_codex_strategy_prompt),
                ("클립보드 복사", self.copy_codex_strategy_prompt),
                ("Codex 제어로 이동", lambda: self._select_control_center_section("codex")),
            ]
        ):
            ttk.Button(strategy_actions, text=label, command=command).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, 8 if index < 2 else 0),
            )
            strategy_actions.columnconfigure(index, weight=1)

        mode_frame = ttk.LabelFrame(codex_strategy_section, text="Automation mode 선택", padding=12)
        mode_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        mode_frame.columnconfigure(1, weight=1)

        self.codex_mode_var = StringVar()
        for option in CODEX_AUTOMATION_MODE_OPTIONS:
            self.codex_mode_choice_by_label[option.title] = option.mode_id
            self.codex_mode_label_by_id[option.mode_id] = option.title

        ttk.Label(mode_frame, text="현재 선택").grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.codex_mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.codex_mode_var,
            state="readonly",
            values=list(self.codex_mode_choice_by_label.keys()),
        )
        self.codex_mode_combo.grid(row=0, column=1, sticky="ew")
        self.codex_mode_combo.bind("<<ComboboxSelected>>", self._on_codex_mode_selected)

        self.codex_mode_status_var = StringVar(value="현재 프로젝트 기준 추천 mode가 여기에 표시됩니다.")
        self.codex_mode_reason_var = StringVar(value="추천 이유가 여기에 표시됩니다.")
        self.codex_mode_result_var = StringVar(value="결과를 다시 볼 위치 안내가 여기에 표시됩니다.")
        self.codex_mode_waiting_var = StringVar(value="무엇을 기다리는지 정보가 여기에 표시됩니다.")

        ttk.Label(mode_frame, textvariable=self.codex_mode_status_var, wraplength=760, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        ttk.Label(mode_frame, textvariable=self.codex_mode_reason_var, wraplength=760, justify="left").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )
        ttk.Label(mode_frame, textvariable=self.codex_mode_result_var, wraplength=760, justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )
        ttk.Label(mode_frame, textvariable=self.codex_mode_waiting_var, wraplength=760, justify="left").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        strategy_body = ttk.Frame(codex_strategy_section)
        strategy_body.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        strategy_body.columnconfigure(0, weight=1)
        strategy_body.columnconfigure(1, weight=1)

        recommended_frame = ttk.LabelFrame(strategy_body, text="추천 운영 정보", padding=12)
        recommended_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        recommended_frame.columnconfigure(0, weight=1)

        self.codex_strategy_summary_var = StringVar(value="시나리오를 고르면 요약이 표시됩니다.")
        self.codex_strategy_type_var = StringVar(value="프리셋 성격: 없음")
        self.codex_strategy_mode_var = StringVar(value="추천 mode: 없음")
        self.codex_strategy_cadence_var = StringVar(value="cadence: 없음")
        self.codex_strategy_worktree_var = StringVar(value="worktree: 없음")

        ttk.Label(
            recommended_frame,
            textvariable=self.codex_strategy_summary_var,
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(recommended_frame, textvariable=self.codex_strategy_type_var, wraplength=360, justify="left").grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(recommended_frame, textvariable=self.codex_strategy_mode_var, wraplength=360, justify="left").grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(
            recommended_frame,
            textvariable=self.codex_strategy_cadence_var,
            wraplength=360,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(4, 0))
        ttk.Label(
            recommended_frame,
            textvariable=self.codex_strategy_worktree_var,
            wraplength=360,
            justify="left",
        ).grid(row=4, column=0, sticky="w", pady=(4, 0))

        roles_frame = ttk.LabelFrame(strategy_body, text="역할 분리", padding=12)
        roles_frame.grid(row=0, column=1, sticky="nsew")
        roles_frame.columnconfigure(0, weight=1)

        self.codex_strategy_use_when_var = StringVar(value="언제 쓰는지 정보가 여기에 표시됩니다.")
        self.codex_strategy_codex_role_var = StringVar(value="Codex 역할: 없음")
        self.codex_strategy_javis_role_var = StringVar(value="javis 역할: 없음")

        ttk.Label(roles_frame, textvariable=self.codex_strategy_use_when_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            roles_frame,
            textvariable=self.codex_strategy_codex_role_var,
            wraplength=360,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            roles_frame,
            textvariable=self.codex_strategy_javis_role_var,
            wraplength=360,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))

        strategy_note_frame = ttk.LabelFrame(codex_strategy_section, text="추가 지시 / follow-up 메모", padding=12)
        strategy_note_frame.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        strategy_note_frame.columnconfigure(0, weight=1)
        ttk.Label(
            strategy_note_frame,
            text="상단장님 스타일, 멈춤 기준, 운영 메모, 재진입 시 꼭 볼 포인트를 짧게 적어둘 수 있습니다.",
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.codex_strategy_note = ScrolledText(strategy_note_frame, height=4, wrap="word")
        self.codex_strategy_note.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        strategy_prompt_frame = ttk.LabelFrame(codex_strategy_section, text="Launch-ready Prompt 초안", padding=12)
        strategy_prompt_frame.grid(row=5, column=0, sticky="nsew", pady=(12, 0))
        strategy_prompt_frame.columnconfigure(0, weight=1)
        strategy_prompt_frame.rowconfigure(1, weight=1)

        self.codex_strategy_prompt_state_var = StringVar(value="프로젝트, 프리셋, mode를 기준으로 launch-ready prompt 초안을 준비합니다.")
        ttk.Label(
            strategy_prompt_frame,
            textvariable=self.codex_strategy_prompt_state_var,
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.codex_strategy_prompt_preview = ScrolledText(strategy_prompt_frame, height=12, wrap="word", state="disabled")
        self.codex_strategy_prompt_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        strategy_bottom = ttk.Frame(codex_strategy_section)
        strategy_bottom.grid(row=6, column=0, sticky="nsew", pady=(12, 0))
        strategy_bottom.columnconfigure(0, weight=1)
        strategy_bottom.columnconfigure(1, weight=1)
        strategy_bottom.rowconfigure(0, weight=1)
        strategy_bottom.rowconfigure(1, weight=1)

        runbook_frame = ttk.LabelFrame(strategy_bottom, text="Launch Checklist / Handoff", padding=12)
        runbook_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        runbook_frame.columnconfigure(0, weight=1)
        runbook_frame.rowconfigure(1, weight=1)
        self.codex_strategy_runbook_state_var = StringVar(value="전략을 고르면 Codex에서 바로 따라할 launch 순서를 보여줍니다.")
        ttk.Label(
            runbook_frame,
            textvariable=self.codex_strategy_runbook_state_var,
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.codex_strategy_runbook_preview = ScrolledText(runbook_frame, height=10, wrap="word", state="disabled")
        self.codex_strategy_runbook_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 8))
        ttk.Button(runbook_frame, text="런북 복사", command=self.copy_codex_strategy_runbook).grid(
            row=2, column=0, sticky="ew"
        )

        runboard_frame = ttk.LabelFrame(strategy_bottom, text="Automation Runboard", padding=12)
        runboard_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        runboard_frame.columnconfigure(0, weight=1)
        runboard_frame.rowconfigure(1, weight=1)
        self.automation_runboard_state_var = StringVar(value="현재 automation 운영 상태 요약이 여기에 표시됩니다.")
        ttk.Label(
            runboard_frame,
            textvariable=self.automation_runboard_state_var,
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.automation_runboard_preview = ScrolledText(runboard_frame, height=10, wrap="word", state="disabled")
        self.automation_runboard_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 8))
        ttk.Button(runboard_frame, text="런보드 복사", command=self.copy_automation_runboard).grid(
            row=2, column=0, sticky="ew"
        )

        triage_frame = ttk.LabelFrame(strategy_bottom, text="Triage / Re-entry Bridge", padding=12)
        triage_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        triage_frame.columnconfigure(0, weight=1)
        triage_frame.rowconfigure(1, weight=1)
        self.triage_bridge_state_var = StringVar(value="결과가 다시 올라왔을 때 어디를 볼지와 다음 행동을 여기에 정리합니다.")
        ttk.Label(
            triage_frame,
            textvariable=self.triage_bridge_state_var,
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.triage_bridge_preview = ScrolledText(triage_frame, height=10, wrap="word", state="disabled")
        self.triage_bridge_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 8))
        ttk.Button(triage_frame, text="브리지 복사", command=self.copy_triage_bridge).grid(
            row=2, column=0, sticky="ew"
        )

        matrix_frame = ttk.LabelFrame(strategy_bottom, text="Safety Guard / Native vs Fallback", padding=12)
        matrix_frame.grid(row=1, column=1, sticky="nsew")
        matrix_frame.columnconfigure(0, weight=1)
        matrix_frame.rowconfigure(1, weight=1)
        self.native_fallback_state_var = StringVar(value="automation을 써야 할 때와 말아야 할 때를 여기서 함께 봅니다.")
        ttk.Label(
            matrix_frame,
            textvariable=self.native_fallback_state_var,
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.native_fallback_preview = ScrolledText(matrix_frame, height=10, wrap="word", state="disabled")
        self.native_fallback_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 8))
        ttk.Button(matrix_frame, text="안전 가드 복사", command=self.copy_native_fallback_matrix).grid(
            row=2, column=0, sticky="ew"
        )

        policy_section.columnconfigure(0, weight=1)
        policy_section.rowconfigure(2, weight=1)
        ttk.Label(
            policy_section,
            text="정책 편집기는 Release 2 판단 엔진과 화면 인식기를 위한 준비 공간입니다. 지금은 정책 구조를 나눠서 길게 적고 저장할 수 있게 먼저 잡습니다.",
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        policy_toolbar = ttk.LabelFrame(policy_section, text="정책 상태", padding=12)
        policy_toolbar.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        policy_toolbar.columnconfigure(0, weight=1)
        policy_toolbar.columnconfigure(1, weight=1)

        policy_summary = ttk.Frame(policy_toolbar)
        policy_summary.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        policy_summary.columnconfigure(0, weight=1)
        ttk.Label(policy_summary, textvariable=self.policy_status_var, wraplength=340, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(policy_summary, textvariable=self.policy_last_edited_var, wraplength=340, justify="left").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(policy_summary, textvariable=self.policy_template_mix_var, wraplength=340, justify="left").grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(policy_summary, textvariable=self.policy_section_state_var, wraplength=340, justify="left").grid(
            row=3, column=0, sticky="w", pady=(4, 0)
        )

        policy_actions = ttk.Frame(policy_toolbar)
        policy_actions.grid(row=0, column=1, sticky="e")
        ttk.Button(
            policy_actions,
            text="현재 섹션 기본값 복원",
            command=self.restore_current_policy_template,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            policy_actions,
            text="전체 기본값 복원",
            command=self.restore_all_policy_templates,
        ).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(policy_actions, text="정책 저장", command=self.save_session).grid(row=0, column=2, sticky="ew")

        note_row = ttk.Frame(policy_toolbar)
        note_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        note_row.columnconfigure(1, weight=1)
        ttk.Label(note_row, text="정책 메모").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Entry(note_row, textvariable=self.policy_note_var).grid(row=0, column=1, sticky="ew")

        policy_frame = ttk.LabelFrame(policy_section, text="Policy Editor Skeleton v1", padding=12)
        policy_frame.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        policy_frame.columnconfigure(0, weight=1)
        policy_frame.rowconfigure(0, weight=1)
        policy_frame.rowconfigure(1, weight=0)

        self.policy_editors: dict[str, ScrolledText] = {}
        self.policy_tab_frames: dict[str, ttk.Frame] = {}
        self.policy_notebook = ttk.Notebook(policy_frame)
        self.policy_notebook.grid(row=0, column=0, sticky="nsew")
        self.policy_notebook.bind("<<NotebookTabChanged>>", self._on_policy_tab_changed)

        for section_key, section_label, section_description in POLICY_SECTION_SPECS:
            tab = ttk.Frame(self.policy_notebook, padding=12)
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(1, weight=1)

            ttk.Label(tab, text=section_description, wraplength=700, justify="left").grid(
                row=0, column=0, sticky="w"
            )

            editor = ScrolledText(tab, height=16, wrap="word")
            editor.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
            editor.bind(
                "<<Modified>>",
                lambda event, key=section_key: self._on_policy_editor_modified(key, event),
            )

            self.policy_notebook.add(tab, text=section_label)
            self.policy_editors[section_key] = editor
            self.policy_tab_frames[section_key] = tab

        ttk.Label(
            policy_frame,
            text="버전 이력과 정책 충돌 분석은 Release 2에서 이 자리 아래로 확장됩니다.",
            wraplength=720,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.policy_note_var.trace_add("write", self._on_policy_note_changed)

        codex_section.columnconfigure(0, weight=1)
        codex_section.rowconfigure(2, weight=1)
        codex_section.rowconfigure(3, weight=1)

        codex_actions = ttk.Frame(codex_section)
        codex_actions.grid(row=0, column=0, sticky="ew")
        for index, (label, command) in enumerate(
            [
                ("창 새로고침", self.refresh_windows),
                ("Codex 포커스", self.focus_codex),
                ("즉시 캡처", self.capture_now),
                ("다음 단계 보내기", self.send_next_step),
                ("자동 루프 시작/중지", self.toggle_auto),
            ]
        ):
            ttk.Button(codex_actions, text=label, command=command).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, 8 if index < 4 else 0),
            )
            codex_actions.columnconfigure(index, weight=1)

        target_settings = ttk.LabelFrame(codex_section, text="Codex 대상 설정", padding=12)
        target_settings.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        target_settings.columnconfigure(1, weight=1)

        self.window_title_var = self._add_entry(target_settings, 0, "창 제목 포함")
        self.process_name_var = self._add_entry(target_settings, 1, "프로세스 이름")

        prompt_frame = ttk.LabelFrame(codex_section, text="단계 큐 / 프롬프트 프리뷰", padding=12)
        prompt_frame.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.columnconfigure(1, weight=2)
        prompt_frame.rowconfigure(4, weight=1)

        self.queue_summary_var = StringVar(value="단계 진행: 없음")
        self.current_step_var = StringVar(value="현재 대기 단계: 없음")
        self.next_step_var = StringVar(value="그다음 단계: 없음")
        self.prompt_status_var = StringVar(value="프롬프트 상태: 원문")

        ttk.Label(prompt_frame, textvariable=self.queue_summary_var, wraplength=420, justify="left").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(prompt_frame, textvariable=self.current_step_var, wraplength=420, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )
        ttk.Label(prompt_frame, textvariable=self.next_step_var, wraplength=420, justify="left").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )
        ttk.Label(prompt_frame, textvariable=self.prompt_status_var, wraplength=420, justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(4, 8)
        )

        queue_box = ttk.Frame(prompt_frame)
        queue_box.grid(row=4, column=0, sticky="nsew", padx=(0, 8))
        queue_box.columnconfigure(0, weight=1)
        queue_box.rowconfigure(1, weight=1)
        ttk.Label(queue_box, text="단계 큐").grid(row=0, column=0, sticky="w")
        self.queue_text = ScrolledText(queue_box, height=10, wrap="word", state="disabled")
        self.queue_text.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

        preview_box = ttk.Frame(prompt_frame)
        preview_box.grid(row=4, column=1, sticky="nsew")
        preview_box.columnconfigure(0, weight=1)
        preview_box.rowconfigure(1, weight=1)
        ttk.Label(preview_box, text="다음 프롬프트").grid(row=0, column=0, sticky="w")
        self.prompt_preview = ScrolledText(preview_box, height=10, wrap="word")
        self.prompt_preview.grid(row=1, column=0, sticky="nsew", pady=(4, 8))
        self.prompt_preview.bind("<<Modified>>", self._on_prompt_modified)
        self.prompt_preview.bind("<Control-Return>", self._on_prompt_send_shortcut)
        self.prompt_preview.bind("<Control-KP_Enter>", self._on_prompt_send_shortcut)

        preview_actions = ttk.Frame(preview_box)
        preview_actions.grid(row=2, column=0, sticky="ew")
        preview_actions.columnconfigure(0, weight=1)
        preview_actions.columnconfigure(1, weight=1)
        preview_actions.columnconfigure(2, weight=1)
        ttk.Button(preview_actions, text="프롬프트 새로고침", command=self.refresh_prompt_preview).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(preview_actions, text="원문으로 되돌리기", command=self.reset_prompt_preview).grid(
            row=0, column=1, sticky="ew", padx=(0, 6)
        )
        ttk.Button(preview_actions, text="미리보기 전송", command=self.send_next_step).grid(
            row=0, column=2, sticky="ew"
        )

        codex_bottom = ttk.Frame(codex_section)
        codex_bottom.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        codex_bottom.columnconfigure(0, weight=1)
        codex_bottom.columnconfigure(1, weight=1)
        codex_bottom.rowconfigure(1, weight=1)

        calibration = ttk.LabelFrame(codex_bottom, text="입력창 캘리브레이션", padding=12)
        calibration.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        calibration.columnconfigure(0, weight=1)
        calibration.columnconfigure(1, weight=1)
        ttk.Label(
            calibration,
            text="딜레이 캡처를 누른 뒤 Codex 입력창 위에 마우스를 올려두면 현재 좌표를 저장합니다.",
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        self.calibration_summary_var = StringVar(value="저장된 좌표가 없습니다.")
        self.calibration_status_var = StringVar(value="캘리브레이션 대기")
        ttk.Label(calibration, textvariable=self.calibration_summary_var, wraplength=360, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        ttk.Label(calibration, textvariable=self.calibration_status_var, wraplength=360, justify="left").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(4, 8)
        )
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

        status = ttk.LabelFrame(codex_bottom, text="실행 상태 / 후보", padding=12)
        status.grid(row=0, column=1, sticky="nsew")
        status.columnconfigure(0, weight=1)
        status.rowconfigure(6, weight=1)

        self.next_step_label = ttk.Label(status, text="다음 단계 인덱스: 0")
        self.next_step_label.grid(row=0, column=0, sticky="w")
        self.last_capture_label = ttk.Label(status, text="마지막 캡처: 없음", wraplength=360, justify="left")
        self.last_capture_label.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.auto_label = ttk.Label(status, text="자동 루프: 중지")
        self.auto_label.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.target_window_label = ttk.Label(status, text="타깃 창: 없음", wraplength=360, justify="left")
        self.target_window_label.grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.target_status_label = ttk.Label(status, text="타깃 상태: 없음", wraplength=360, justify="left")
        self.target_status_label.grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.target_reason_label = ttk.Label(status, text="선택 근거: 없음", wraplength=360, justify="left")
        self.target_reason_label.grid(row=5, column=0, sticky="w", pady=(8, 0))

        self.windows_list = ScrolledText(status, height=12, wrap="none")
        self.windows_list.grid(row=6, column=0, sticky="nsew", pady=(8, 0))

        safety_section.columnconfigure(0, weight=1)

        automation_settings = ttk.LabelFrame(safety_section, text="자동화 / 안전 설정", padding=12)
        automation_settings.grid(row=0, column=0, sticky="ew")
        automation_settings.columnconfigure(1, weight=1)

        self.poll_interval_var = self._add_entry(automation_settings, 0, "폴링 간격(초)")
        self.stable_cycles_var = self._add_entry(automation_settings, 1, "안정 판정 횟수")
        self.cooldown_var = self._add_entry(automation_settings, 2, "전송 쿨다운(초)")
        self.threshold_var = self._add_entry(automation_settings, 3, "시그니처 임계값")
        self.calibration_delay_var = self._add_entry(automation_settings, 4, "캘리브레이션 대기(초)")
        self.click_x_var = self._add_entry(automation_settings, 5, "입력창 상대 X")
        self.click_y_var = self._add_entry(automation_settings, 6, "입력창 상대 Y")
        self.submit_var = self._add_check(automation_settings, 7, "전송 시 Enter")
        self.dry_run_var = self._add_check(automation_settings, 8, "DRY RUN")

        safety_actions = ttk.Frame(safety_section)
        safety_actions.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        for index, (label, command) in enumerate(
            [
                ("사이클 실행", self.run_cycle_once),
                ("자동 루프 시작/중지", self.toggle_auto),
                ("즉시 캡처", self.capture_now),
            ]
        ):
            ttk.Button(safety_actions, text=label, command=command).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, 8 if index < 2 else 0),
            )
            safety_actions.columnconfigure(index, weight=1)

        evidence_section.columnconfigure(0, weight=1)
        evidence_section.rowconfigure(1, weight=1)
        evidence_toolbar = ttk.Frame(evidence_section)
        evidence_toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Button(evidence_toolbar, text="즉시 캡처", command=self.capture_now).pack(side=LEFT, padx=(0, 8))
        ttk.Button(evidence_toolbar, text="접근성 확인", command=self.inspect_accessibility).pack(side=LEFT)

        log_frame = ttk.LabelFrame(evidence_section, text="로그", padding=12)
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = ScrolledText(log_frame, height=18, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")

        model_voice_section.columnconfigure(0, weight=1)
        ttk.Label(
            model_voice_section,
            text=(
                "Release 1에서는 모델 / 음성 섹션을 구조만 먼저 준비합니다.\n"
                "이후 OpenAI 모델 선택, push-to-talk, TTS, 음성 브리핑 설정이 이 영역으로 확장됩니다."
            ),
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        advanced_section.columnconfigure(0, weight=1)
        diagnostics = ttk.LabelFrame(advanced_section, text="고급 진단", padding=12)
        diagnostics.grid(row=0, column=0, sticky="ew")
        for index, (label, command) in enumerate(
            [
                ("접근성 확인", self.inspect_accessibility),
                ("사이클 실행", self.run_cycle_once),
                ("창 새로고침", self.refresh_windows),
            ]
        ):
            ttk.Button(diagnostics, text=label, command=command).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, 8 if index < 2 else 0),
            )
            diagnostics.columnconfigure(index, weight=1)
        ttk.Label(
            diagnostics,
            text="향후 음성 / 재판단 / 실험 기능은 이 섹션에서 플래그 기반으로 확장할 예정입니다.",
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(12, 0))

        self._select_control_center_section("project")
        self._refresh_control_center_header()

    def _create_control_section(self, section_id: str, label: str) -> ttk.Frame:
        button = ttk.Button(
            self.control_nav,
            text=label,
            command=lambda current=section_id: self._select_control_center_section(current),
        )
        button.pack(fill="x", pady=(0, 8))
        frame = ttk.Frame(self.control_content, padding=4)
        frame.grid(row=0, column=0, sticky="nsew")
        self.control_nav_buttons[section_id] = button
        self.control_section_frames[section_id] = frame
        self.control_section_labels[section_id] = label
        return frame

    def _select_control_center_section(self, section_id: str) -> None:
        self.control_section_var.set(section_id)
        for current_id, frame in self.control_section_frames.items():
            if current_id == section_id:
                frame.grid()
            else:
                frame.grid_remove()

        for current_id, button in self.control_nav_buttons.items():
            label = self.control_section_labels[current_id]
            button.configure(text=f"• {label}" if current_id == section_id else label)

    def _refresh_control_center_header(self) -> None:
        project_label = self.session.project.project_summary or self.session.project.target_outcome or "프로젝트 정보 미입력"
        if self.runtime.auto_running:
            state_label = "자동 감시 중"
        elif self.runtime.operator_paused:
            state_label = "보류 중"
        else:
            state_label = "대기"

        saved_label = self.last_saved_at.replace("T", " ") if self.last_saved_at else "미저장"
        target_label = self.runtime.last_target_title or "타깃 미확정"
        self.control_header_project_var.set(project_label)
        self.control_header_status_var.set(f"세션 {saved_label} | 상태 {state_label} | {target_label}")

    def _codex_strategy_label_for_id(self, preset_id: str) -> str:
        return self.codex_strategy_label_by_id.get(
            preset_id,
            next(iter(self.codex_strategy_label_by_id.values()), ""),
        )

    def _codex_mode_label_for_id(self, mode_id: str) -> str:
        return self.codex_mode_label_by_id.get(
            mode_id,
            next(iter(self.codex_mode_label_by_id.values()), ""),
        )

    def _current_codex_strategy_preset_id(self) -> str:
        label = self.codex_strategy_var.get().strip()
        return self.codex_strategy_choice_by_label.get(
            label,
            next(iter(self.codex_strategy_choice_by_label.values()), ""),
        )

    def _current_codex_mode_id(self) -> str:
        label = self.codex_mode_var.get().strip()
        return self.codex_mode_choice_by_label.get(
            label,
            next(iter(self.codex_mode_choice_by_label.values()), ""),
        )

    def _refresh_codex_strategy_panel(self, session: SessionConfig | None = None) -> None:
        active_session = session
        if active_session is None:
            try:
                active_session = self._collect_session()
            except Exception:
                active_session = self.session

        preset = active_session.codex_strategy.selected_preset()
        selected_mode = active_session.codex_strategy.selected_mode()
        decision = self.engine.recommend_codex_automation_mode(active_session, self.runtime)
        recommended_option = get_codex_automation_mode_option(decision.recommended_mode_id)
        effective_option = get_codex_automation_mode_option(decision.effective_mode_id)
        display_label = self._codex_strategy_label_for_id(preset.preset_id)
        if display_label and self.codex_strategy_var.get() != display_label:
            self.codex_strategy_var.set(display_label)
        mode_label = self._codex_mode_label_for_id(selected_mode.mode_id)
        if mode_label and self.codex_mode_var.get() != mode_label:
            self.codex_mode_var.set(mode_label)

        self.codex_strategy_status_var.set(
            f"추천 프리셋: {preset.title} | 프리셋 성격은 {preset.automation_type} 입니다."
        )
        self.codex_strategy_summary_var.set(preset.summary)
        self.codex_strategy_type_var.set(f"프리셋 성격: {preset.automation_type}")
        self.codex_strategy_mode_var.set(f"추천 mode: {recommended_option.title} | 실제 launch: {effective_option.title}")
        self.codex_strategy_cadence_var.set(f"cadence: {decision.cadence_hint}")
        self.codex_strategy_worktree_var.set(f"worktree: {decision.worktree_hint}")
        self.codex_strategy_use_when_var.set(f"이럴 때 사용: {preset.use_when}")
        self.codex_strategy_codex_role_var.set(f"Codex 역할: {preset.codex_role}")
        self.codex_strategy_javis_role_var.set(f"javis 역할: {preset.javis_role}")
        self.codex_mode_status_var.set(
            f"추천 mode: {recommended_option.title} | 현재 선택: {selected_mode.title} | 실제 launch: {effective_option.title}"
        )
        self.codex_mode_reason_var.set(decision.effective_reason)
        self.codex_mode_result_var.set(f"결과를 다시 볼 위치: {decision.result_location}")
        self.codex_mode_waiting_var.set(f"지금 기다리는 것: {decision.waiting_for}")

        prompt = self.engine.build_codex_strategy_prompt(active_session, self.runtime)
        self._current_codex_strategy_prompt = prompt
        self.codex_strategy_prompt_state_var.set(
            "현재 프로젝트, 프리셋, mode를 합쳐 Codex 앱에 바로 옮길 수 있는 launch-ready prompt를 만들었습니다."
        )
        self._set_readonly_text(self.codex_strategy_prompt_preview, prompt)

        runbook = self.engine.build_codex_strategy_runbook(active_session, self.runtime)
        self._current_codex_strategy_runbook = runbook
        self.codex_strategy_runbook_state_var.set(
            "선택한 mode를 Codex 앱으로 실제로 옮길 때 따라갈 launch 순서를 정리했습니다."
        )
        self._set_readonly_text(self.codex_strategy_runbook_preview, runbook)

        runboard = self.engine.build_automation_runboard(active_session, self.runtime)
        self._current_automation_runboard = runboard
        self.automation_runboard_state_var.set(
            "현재 전략, 기다리는 것, follow-up 메모, 다음 확인 행동을 runboard 형태로 보여줍니다."
        )
        self._set_readonly_text(self.automation_runboard_preview, runboard)

        triage_bridge = self.engine.build_triage_summary_bridge(active_session, self.runtime)
        self._current_triage_bridge = triage_bridge
        self.triage_bridge_state_var.set(
            "Codex 결과가 다시 올라왔을 때 어디를 열어보고 어떤 순서로 읽을지 bridge 형태로 정리했습니다."
        )
        self._set_readonly_text(self.triage_bridge_preview, triage_bridge)

        matrix = self.engine.build_native_fallback_matrix(active_session, self.runtime)
        self._current_native_fallback_matrix = matrix
        self.native_fallback_state_var.set(
            "automation을 써야 할 때와 말아야 할 때, 그리고 fallback을 고려할 경계를 현재 전략 기준으로 같이 보여줍니다."
        )
        self._set_readonly_text(self.native_fallback_preview, matrix)

    def _on_codex_strategy_selected(self, _event=None) -> None:
        self._refresh_codex_strategy_panel()

    def _on_codex_mode_selected(self, _event=None) -> None:
        self._refresh_codex_strategy_panel()

    def refresh_codex_strategy_prompt(self) -> None:
        try:
            self.session = self._collect_session()
            self._refresh_codex_strategy_panel(self.session)
            self._save_session_quietly()
            self._log("Codex 전략 프리셋과 mode 기준으로 launch-ready 초안을 다시 만들었습니다.")
        except Exception as exc:
            messagebox.showerror("Codex 전략 새로고침 실패", str(exc))

    def _copy_text_to_clipboard(self, *, title: str, text: str, success_log: str) -> None:
        if not text.strip():
            messagebox.showerror(title, "복사할 내용이 아직 없습니다.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._log(success_log)

    def copy_codex_strategy_prompt(self) -> None:
        try:
            if not self._current_codex_strategy_prompt.strip():
                self._refresh_codex_strategy_panel()
            self._copy_text_to_clipboard(
                title="Codex 전략 프롬프트 복사",
                text=self._current_codex_strategy_prompt,
                success_log="현재 Codex 전략 prompt 초안을 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("클립보드 복사 실패", str(exc))

    def copy_codex_strategy_runbook(self) -> None:
        try:
            if not self._current_codex_strategy_runbook.strip():
                self._refresh_codex_strategy_panel()
            self._copy_text_to_clipboard(
                title="Codex 전략 런북 복사",
                text=self._current_codex_strategy_runbook,
                success_log="현재 Codex 전략 런북을 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("런북 복사 실패", str(exc))

    def copy_automation_runboard(self) -> None:
        try:
            if not self._current_automation_runboard.strip():
                self._refresh_codex_strategy_panel()
            self._copy_text_to_clipboard(
                title="Automation Runboard 복사",
                text=self._current_automation_runboard,
                success_log="Automation Runboard를 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("런보드 복사 실패", str(exc))

    def copy_triage_bridge(self) -> None:
        try:
            if not self._current_triage_bridge.strip():
                self._refresh_codex_strategy_panel()
            self._copy_text_to_clipboard(
                title="Triage Bridge 복사",
                text=self._current_triage_bridge,
                success_log="Triage / Re-entry Bridge를 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("브리지 복사 실패", str(exc))

    def copy_native_fallback_matrix(self) -> None:
        try:
            if not self._current_native_fallback_matrix.strip():
                self._refresh_codex_strategy_panel()
            self._copy_text_to_clipboard(
                title="Automation Safety Guard 복사",
                text=self._current_native_fallback_matrix,
                success_log="Automation Safety Guard와 Native vs Fallback 매트릭스를 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("안전 가드 복사 실패", str(exc))

    def _set_popup_topmost(self, enabled: bool) -> None:
        try:
            self.root.attributes("-topmost", enabled)
        except TclError:
            pass

    def _set_wraplength(self, widget, wraplength: int) -> None:
        widget.configure(wraplength=max(220, wraplength))

    def _set_popup_geometry(self, width: int, height: int) -> None:
        self.root.update_idletasks()
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        clamped_x = min(max(x, 0), max(screen_width - width, 0))
        clamped_y = min(max(y, 0), max(screen_height - height - 48, 0))
        self.root.geometry(f"{width}x{height}+{clamped_x}+{clamped_y}")

    def _layout_popup_action_bar(self, popup_width: int) -> None:
        two_row = popup_width < 410
        for index, button in enumerate(self.popup_action_buttons):
            button.grid_forget()
            if two_row:
                row = index // 2
                column = index % 2
                padx = (0, 6) if column == 0 else 0
                pady = (0, 6) if row == 0 else 0
                button.grid(row=row, column=column, sticky="ew", padx=padx, pady=pady)
            else:
                button.grid(
                    row=0,
                    column=index,
                    sticky="ew",
                    padx=(0, 6) if index < 3 else 0,
                    pady=0,
                )

    def _update_popup_density(self) -> None:
        self.root.update_idletasks()
        popup_width = max(self.root.winfo_width(), self._popup_compact_size[0])
        text_wrap = popup_width - 88
        project_wrap = popup_width - 180

        self._set_wraplength(self.popup_project_label, project_wrap)
        self._set_wraplength(self.popup_status_label, text_wrap)
        self._set_wraplength(self.popup_compact_hint_label, text_wrap)
        self._set_wraplength(self.popup_reason_label, text_wrap)
        self._set_wraplength(self.popup_next_label, text_wrap)
        self._set_wraplength(self.popup_detail_label, text_wrap)
        self._set_wraplength(self.popup_last_event_label, text_wrap)
        self._layout_popup_action_bar(popup_width)

    def _apply_popup_compact_mode(self) -> None:
        if self._popup_compact:
            self.popup_compact_frame.grid()
            self.popup_detail_frame.grid_remove()
            self.popup_footer_frame.grid_remove()
            self.compact_button_var.set("자세히")
            self._set_popup_geometry(*self._popup_compact_size)
        else:
            self.popup_compact_frame.grid_remove()
            self.popup_detail_frame.grid()
            self.popup_footer_frame.grid()
            self.compact_button_var.set("간단히")
            self._set_popup_geometry(*self._popup_expanded_size)
        self._update_popup_density()

    def _position_control_center_near_popup(self) -> None:
        self.root.update_idletasks()
        self.control_center.update_idletasks()
        popup_x = self.root.winfo_x()
        popup_y = self.root.winfo_y()
        popup_width = self.root.winfo_width()
        center_width = self.control_center.winfo_width()
        center_height = self.control_center.winfo_height()
        if center_width <= 1:
            center_width = 1280
        if center_height <= 1:
            center_height = 940
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_width = min(center_width, max(screen_width - 40, 320))
        center_height = min(center_height, max(screen_height - 72, 360))
        gap = 18

        desired_x = popup_x + popup_width + gap
        if desired_x + center_width > screen_width - 16:
            desired_x = popup_x - center_width - gap
        if desired_x < 16:
            desired_x = max((screen_width - center_width) // 2, 16)

        desired_y = popup_y - 8
        if desired_y + center_height > screen_height - 48:
            desired_y = max(screen_height - center_height - 48, 16)
        desired_y = max(desired_y, 16)

        self.control_center.geometry(f"{center_width}x{center_height}+{desired_x}+{desired_y}")

    def _on_popup_configure(self, event=None) -> None:
        if event is not None and event.widget is not self.root:
            return
        self._update_popup_density()

    def open_control_center(self) -> None:
        self._set_popup_topmost(False)
        self._select_control_center_section("project")
        self._refresh_control_center_header()
        self._refresh_project_home()
        self._position_control_center_near_popup()
        self.control_center.deiconify()
        self.control_center.lift()
        self.control_center.focus_force()

    def hide_control_center(self) -> None:
        self.control_center.withdraw()
        self._set_popup_topmost(True)
        self.root.lift()
        self.root.focus_force()

    def _show_future_action_placeholder(self, feature_name: str, description: str) -> None:
        self._log(f"준비 중인 액션: {feature_name}")
        messagebox.showinfo(feature_name, description)

    def resume_after_pause(self) -> None:
        self.runtime.clear_operator_pause()
        self._save_session_quietly()
        self._refresh_runtime_labels()
        self._log("보류 상태를 해제했습니다. 이제 다시 진행할 수 있습니다.")

    def perform_surface_action(self, action_id: str) -> None:
        action_label = next(
            (action.label for action in self._surface_state.actions if action.action_id == action_id),
            action_id,
        )
        handlers = {
            "continue": self.send_next_step,
            "resume_ready": self.resume_after_pause,
            "start_auto": self.toggle_auto,
            "pause_auto": self.pause_automation,
            "show_summary": self.show_status_summary,
            "open_settings": self.open_control_center,
            "refresh_windows": self.refresh_windows,
            "focus_codex": self.focus_codex,
            "capture_now": self.capture_now,
            "voice_brief": lambda: self._show_future_action_placeholder(
                "음성 브리핑",
                "음성 브리핑은 Voice 단계에서 연결될 예정입니다.",
            ),
            "rejudge": lambda: self._show_future_action_placeholder(
                "재판단",
                "재판단 액션은 OpenAI 판단 엔진이 붙는 단계에서 연결될 예정입니다.",
            ),
        }
        handler = handlers.get(action_id)
        if handler is None:
            self._log(f"아직 연결되지 않은 팝업 액션입니다: {action_id}")
            return
        if action_id in {"open_settings", "show_summary", "pause_auto", "resume_ready"}:
            self._log(f"팝업 액션 실행: {action_label}")
        handler()

    def _render_popup_actions(self) -> None:
        actions = self._surface_state.actions[:4]
        for index, button in enumerate(self.popup_action_buttons):
            if index >= len(actions):
                button.configure(text="")
                button.state(["disabled"])
                continue
            action = actions[index]
            button.configure(
                text=action.label,
                command=lambda action_id=action.action_id: self.perform_surface_action(action_id),
                style="PopupPrimary.TButton" if index == 0 else "PopupSecondary.TButton",
            )
            if action.enabled:
                button.state(["!disabled"])
            else:
                button.state(["disabled"])
        self._update_popup_density()

    def toggle_popup_compact(self) -> None:
        self._popup_compact = not self._popup_compact
        self._apply_popup_compact_mode()

    def pause_automation(self) -> None:
        reason = "팝업에서 보류를 요청했습니다."
        if self.runtime.auto_running:
            self.stop_event.set()
            self.runtime.auto_running = False
            reason = "팝업에서 보류를 요청해 자동 감시를 멈췄습니다."
        self.runtime.set_operator_pause(reason)
        self._save_session_quietly()
        self._refresh_runtime_labels()
        self._log(reason)

    def show_status_summary(self) -> None:
        if self._popup_compact:
            self.toggle_popup_compact()
            self._log("팝업 상세 카드를 다시 펼쳤습니다.")
            return
        lines = [
            f"상태: {self._surface_state.badge_label}",
            f"현재: {self._surface_state.title}",
            f"요약: {self._surface_state.summary}",
            f"이유: {self._surface_state.reason}",
            f"다음 행동: {self._surface_state.next_action}",
            f"진행도: {self._surface_state.progress_label}",
            f"상세: {self._surface_state.detail_label}",
            f"위험: {self._surface_state.risk_label}",
        ]
        messagebox.showinfo("javis 요약", "\n\n".join(lines))

    def _close_application(self) -> None:
        self.stop_event.set()
        self.runtime.auto_running = False
        try:
            self.control_center.destroy()
        except TclError:
            pass
        self.root.destroy()

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

    def _set_scrolled_text(self, widget: ScrolledText, text: str) -> None:
        widget.delete("1.0", END)
        widget.insert("1.0", text)
        try:
            widget.edit_modified(False)
        except TclError:
            pass

    def _set_readonly_text(self, widget: ScrolledText, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _policy_input_snapshot(self) -> tuple[dict[str, str], str]:
        sections: dict[str, str] = {}
        for section_key, _section_label, _section_description in POLICY_SECTION_SPECS:
            editor = self.policy_editors.get(section_key)
            if editor is None:
                sections[section_key] = self.session.policy.section_text(section_key).strip()
            else:
                sections[section_key] = editor.get("1.0", END).strip()
        return sections, self.policy_note_var.get().strip()

    def _current_policy_section_key(self) -> str:
        current_tab = self.policy_notebook.select()
        for section_key, frame in self.policy_tab_frames.items():
            if str(frame) == current_tab:
                return section_key
        return POLICY_SECTION_SPECS[0][0]

    def _recalculate_policy_dirty(self) -> None:
        sections, note = self._policy_input_snapshot()
        self._policy_dirty = note != self.session.policy.edit_note.strip()
        if self._policy_dirty:
            return

        for section_key, _section_label, _section_description in POLICY_SECTION_SPECS:
            if sections.get(section_key, "") != self.session.policy.section_text(section_key).strip():
                self._policy_dirty = True
                return

    def _refresh_policy_editor_state(self) -> None:
        sections, _note = self._policy_input_snapshot()
        templates = self.session.policy.default_templates()
        active_section = self._current_policy_section_key()
        active_label = self.session.policy.section_label(active_section)
        active_is_default = sections.get(active_section, "").strip() == templates.get(active_section, "").strip()

        customized_count = sum(
            0 if sections.get(section_key, "").strip() == templates.get(section_key, "").strip() else 1
            for section_key, _section_label, _section_description in POLICY_SECTION_SPECS
        )
        default_count = len(POLICY_SECTION_SPECS) - customized_count

        if self._policy_dirty:
            self.policy_status_var.set("정책 저장 상태: 저장 전 변경 있음")
            edited_at = self._policy_live_edited_at or "방금 수정됨"
            edited_section = self.session.policy.section_label(self._policy_last_edited_section or active_section)
        elif self.last_saved_at:
            saved_label = self.last_saved_at.replace("T", " ")[:16]
            self.policy_status_var.set(f"정책 저장 상태: 저장됨 ({saved_label})")
            edited_at = self.session.policy.last_edited_at or "없음"
            edited_section = self.session.policy.section_label(self.session.policy.last_edited_section or active_section)
        else:
            self.policy_status_var.set("정책 저장 상태: 아직 저장 전")
            edited_at = self.session.policy.last_edited_at or "없음"
            edited_section = self.session.policy.section_label(self.session.policy.last_edited_section or active_section)

        self.policy_last_edited_var.set(f"최근 수정: {edited_at} | 섹션: {edited_section}")
        self.policy_template_mix_var.set(f"커스텀 {customized_count} / 기본 {default_count}")
        current_mode = "기본 템플릿" if active_is_default else "커스텀"
        self.policy_section_state_var.set(f"현재 섹션: {active_label} | {current_mode}")

    def _load_policy_editors(self) -> None:
        self._policy_loading = True
        for section_key, _section_label, _section_description in POLICY_SECTION_SPECS:
            self._set_scrolled_text(self.policy_editors[section_key], self.session.policy.section_text(section_key))
        self.policy_note_var.set(self.session.policy.edit_note)
        self._policy_loading = False
        self._policy_dirty = False
        self._policy_live_edited_at = ""
        self._policy_last_edited_section = self.session.policy.last_edited_section
        self._refresh_policy_editor_state()

    def _record_policy_change(self, section_key: str) -> None:
        if self._policy_loading:
            return
        self._policy_live_edited_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._policy_last_edited_section = section_key
        self._recalculate_policy_dirty()
        self._refresh_policy_editor_state()

    def _on_policy_editor_modified(self, section_key: str, _event=None) -> None:
        editor = self.policy_editors[section_key]
        if not editor.edit_modified():
            return
        editor.edit_modified(False)
        self._record_policy_change(section_key)

    def _on_policy_note_changed(self, *_args) -> None:
        self._record_policy_change(self._current_policy_section_key())

    def _on_policy_tab_changed(self, _event=None) -> None:
        self._refresh_policy_editor_state()

    def restore_current_policy_template(self) -> None:
        section_key = self._current_policy_section_key()
        default_text = self.session.policy.default_for(section_key)
        self._policy_loading = True
        self._set_scrolled_text(self.policy_editors[section_key], default_text)
        self._policy_loading = False
        self._record_policy_change(section_key)
        self._log(f"{self.session.policy.section_label(section_key)} 정책을 기본 템플릿으로 복원했습니다.")

    def restore_all_policy_templates(self) -> None:
        templates = self.session.policy.default_templates()
        self._policy_loading = True
        for section_key, _section_label, _section_description in POLICY_SECTION_SPECS:
            self._set_scrolled_text(self.policy_editors[section_key], templates.get(section_key, ""))
        self.policy_note_var.set("")
        self._policy_loading = False
        self._record_policy_change(POLICY_SECTION_SPECS[0][0])
        self._log("정책 전체를 기본 템플릿으로 복원했습니다.")

    def _build_persisted_state(self) -> PersistedSessionState:
        return PersistedSessionState(
            schema_version=self.session_schema_version,
            saved_at=self.last_saved_at,
            log_path=self.log_reference_path,
            session=SessionConfig.from_dict(self.session.to_dict()),
            runtime=RuntimeState.from_persisted_dict(self.runtime.to_persisted_dict()),
            recent_projects=list(self.recent_projects),
        )

    def _refresh_persistence_panel(self) -> None:
        self.schema_version_var.set(f"세션 스키마 v{self.session_schema_version}")
        self.last_saved_var.set(
            f"마지막 저장: {self.last_saved_at.replace('T', ' ') if self.last_saved_at else '없음'}"
        )
        self.log_reference_var.set(f"로그 파일: {self.log_reference_path or '없음'}")

        values = [item.display_label() for item in self.recent_projects]
        self.recent_projects_combo["values"] = values
        if values:
            current_value = self.recent_project_var.get()
            if current_value in values:
                self.recent_projects_combo.set(current_value)
            else:
                self.recent_projects_combo.current(0)
            self.load_recent_button.state(["!disabled"])
        else:
            self.recent_project_var.set("")
            self.load_recent_button.state(["disabled"])
        self._refresh_control_center_header()
        self._refresh_project_home()

    def _selected_recent_project_entry(self):
        index = self.recent_projects_combo.current()
        if 0 <= index < len(self.recent_projects):
            return self.recent_projects[index]
        if self.recent_projects:
            return self.recent_projects[0]
        return None

    def _on_recent_project_selected(self, _event=None) -> None:
        self._refresh_project_home()

    def _refresh_project_home(self) -> None:
        steps = self.session.project.steps()
        total_steps = len(steps)
        project_title = self.session.project.project_summary or self.session.project.target_outcome or "프로젝트 정보 미입력"
        target_text = self.session.project.target_outcome or "목표 수준이 아직 없습니다."
        current_strategy = self.session.codex_strategy.selected_preset()
        current_decision = self.engine.recommend_codex_automation_mode(self.session, self.runtime)
        current_mode = get_codex_automation_mode_option(current_decision.effective_mode_id)
        strategy_text = (
            f"운영 프로필: {current_strategy.title} | 선택 mode: {self.session.codex_strategy.selected_mode().title} | "
            f"실제 launch: {current_mode.title}"
        )
        if self.session.codex_strategy.custom_instruction.strip():
            strategy_text += "\n추가 지시: " + self.session.codex_strategy.custom_instruction.strip()
        completed_steps = min(self.runtime.next_step_index, total_steps)
        if total_steps == 0:
            progress_text = "현재 단계 정보가 없습니다."
        elif self.runtime.next_step_index >= total_steps:
            progress_text = f"현재 계획을 모두 전송했습니다. 진행 {completed_steps}/{total_steps}"
        else:
            current_step = steps[self.runtime.next_step_index]
            progress_text = f"현재 단계 {self.runtime.next_step_index + 1}/{total_steps}: {current_step}"

        capture_name = Path(self.runtime.last_capture_path).name if self.runtime.last_capture_path else "최근 캡처 없음"
        status_text = self.runtime.last_target_reason or self._surface_state.summary or "마지막 상태 정보가 아직 없습니다."

        self.project_home_title_var.set(project_title)
        self.project_home_target_var.set(f"목표 수준: {target_text}")
        self.project_home_strategy_var.set(strategy_text)
        self.project_home_progress_var.set(progress_text)
        self.project_home_status_var.set(f"마지막 상태: {status_text}")
        self.project_home_capture_var.set(f"최근 캡처: {capture_name}")

        entry = self._selected_recent_project_entry()
        if entry is None:
            self.recent_project_summary_var.set("최근 프로젝트가 없습니다.")
            self.recent_project_target_var.set("세션을 저장하면 이어서 불러올 프로젝트가 이곳에 쌓입니다.")
            self.recent_project_strategy_var.set("운영 프로필 정보 없음")
            self.recent_project_progress_var.set("진행 정보 없음")
            self.recent_project_capture_var.set("최근 캡처 없음")
            return

        title = entry.project_summary or entry.target_outcome or "이름 없는 프로젝트"
        target = entry.target_outcome or "목표 수준 미입력"
        stamp = entry.saved_at.replace("T", " ") if entry.saved_at else "저장 시각 없음"
        progress_current = min(entry.next_step_index, max(entry.total_steps, 0))
        capture_preview = Path(entry.last_capture_path).name if entry.last_capture_path else "최근 캡처 없음"
        recent_strategy = entry.session.codex_strategy.selected_preset()
        recent_decision = self.engine.recommend_codex_automation_mode(entry.session, entry.runtime)
        recent_mode = get_codex_automation_mode_option(recent_decision.effective_mode_id)
        recent_strategy_text = (
            f"운영 프로필: {recent_strategy.title} | 선택 mode: {entry.session.codex_strategy.selected_mode().title} | "
            f"실제 launch: {recent_mode.title}"
        )
        if entry.session.codex_strategy.custom_instruction.strip():
            recent_strategy_text += "\n추가 지시: " + entry.session.codex_strategy.custom_instruction.strip()
        self.recent_project_summary_var.set(f"{title}\n저장 시각: {stamp}")
        self.recent_project_target_var.set(f"목표 수준: {target}")
        self.recent_project_strategy_var.set(recent_strategy_text)
        self.recent_project_progress_var.set(f"진행 {progress_current}/{entry.total_steps}")
        self.recent_project_capture_var.set(f"최근 캡처: {capture_preview}")

    def load_recent_project_selection(self) -> None:
        index = self.recent_projects_combo.current()
        if index < 0 or index >= len(self.recent_projects):
            messagebox.showerror("최근 프로젝트 불러오기 실패", "불러올 최근 프로젝트를 먼저 선택해 주세요.")
            return

        if self.runtime.auto_running:
            self.stop_event.set()
            self.runtime.auto_running = False

        entry = self.recent_projects[index]
        self.session = SessionConfig.from_dict(entry.session.to_dict())
        self.runtime = RuntimeState.from_persisted_dict(entry.runtime.to_persisted_dict())
        self._load_session()
        self._refresh_calibration_summary()
        self._refresh_persistence_panel()
        self._refresh_prompt_panel_from_current_session()
        self._refresh_runtime_labels()
        self._save_session_quietly()
        self._log(f"최근 프로젝트를 불러왔습니다. {entry.display_label()}")

    def _set_prompt_editor_text(self, text: str) -> None:
        current = self.prompt_preview.get("1.0", END).rstrip("\n")
        if current == text:
            return
        self._suspend_prompt_modified = True
        self.prompt_preview.delete("1.0", END)
        self.prompt_preview.insert("1.0", text)
        self.prompt_preview.edit_modified(False)
        self._suspend_prompt_modified = False

    def _sync_prompt_draft_from_editor(self) -> None:
        if self.runtime.prompt_step_index is None:
            return
        draft = self.prompt_preview.get("1.0", END).rstrip("\n")
        self.runtime.update_prompt_draft(draft)

    def _refresh_prompt_panel_from_current_session(self) -> None:
        preview = self.engine.build_prompt_preview(self.session, self.runtime)
        queue = self.engine.build_step_queue(self.session, self.runtime)
        self._current_preview = preview
        self._current_queue = queue
        self._refresh_surface_state()
        self._render_prompt_panel(preview, queue)
        self._refresh_codex_strategy_panel(self.session)
        self._refresh_popup_shell()

    def _render_prompt_panel(self, preview: PromptPreview, queue: list[StepQueueItem]) -> None:
        total_steps = len(queue)
        completed_steps = min(self.runtime.next_step_index, total_steps)
        self.queue_summary_var.set(f"단계 진행: 완료 {completed_steps} / 전체 {total_steps}")

        if not queue:
            self.current_step_var.set("현재 대기 단계: 단계가 없습니다.")
            self.next_step_var.set("그다음 단계: 단계가 없습니다.")
            self.prompt_status_var.set("프롬프트 상태: 단계 목록을 먼저 입력해 주세요.")
            queue_lines = ["단계가 없습니다."]
            desired_prompt = ""
        elif preview.is_complete:
            self.current_step_var.set("현재 대기 단계: 모든 단계를 전송했습니다.")
            self.next_step_var.set("그다음 단계: 추가 단계가 없습니다.")
            self.prompt_status_var.set("프롬프트 상태: 완료")
            queue_lines = [item.display_line() for item in queue]
            desired_prompt = ""
        else:
            self.current_step_var.set(
                f"현재 대기 단계: {preview.step_index + 1}/{preview.total_steps} {preview.step_title}"
            )
            next_index = preview.step_index + 1
            if next_index < len(queue):
                next_item = queue[next_index]
                self.next_step_var.set(f"그다음 단계: {next_item.index + 1}/{next_item.total} {next_item.title}")
            else:
                self.next_step_var.set("그다음 단계: 이번 단계가 마지막입니다.")
            self.prompt_status_var.set(
                f"프롬프트 상태: {preview.source_label} | 포인터는 실제 전송 성공 뒤에만 증가합니다."
            )
            queue_lines = [item.display_line() for item in queue]
            desired_prompt = preview.draft_prompt

        self._set_readonly_text(self.queue_text, "\n".join(queue_lines))
        self._set_prompt_editor_text(desired_prompt)

    def _on_prompt_modified(self, _event=None) -> None:
        if self._suspend_prompt_modified:
            self.prompt_preview.edit_modified(False)
            return
        self._sync_prompt_draft_from_editor()
        self._refresh_prompt_panel_from_current_session()
        self.prompt_preview.edit_modified(False)

    def _on_prompt_send_shortcut(self, _event=None) -> str:
        self.send_next_step()
        return "break"

    def refresh_prompt_preview(self) -> None:
        try:
            self.session = self._collect_session()
            self.runtime.clear_prompt_preview()
            self._refresh_prompt_panel_from_current_session()
            self._save_session_quietly()
            self._log("현재 컨텍스트 기준으로 다음 프롬프트를 다시 만들었습니다.")
        except Exception as exc:
            messagebox.showerror("프롬프트 새로고침 실패", str(exc))

    def reset_prompt_preview(self) -> None:
        try:
            self.session = self._collect_session()
            preview = self.engine.build_prompt_preview(self.session, self.runtime)
            if preview.has_step:
                self.runtime.update_prompt_draft(preview.generated_prompt)
            self._refresh_prompt_panel_from_current_session()
            self._log("프롬프트를 원문으로 되돌렸습니다.")
        except Exception as exc:
            messagebox.showerror("프롬프트 초기화 실패", str(exc))

    def _load_session(self) -> None:
        self._set_scrolled_text(self.project_summary, self.session.project.project_summary)
        self._set_scrolled_text(self.target_outcome, self.session.project.target_outcome)
        self._set_scrolled_text(self.steps_text, self.session.project.steps_text)
        self.codex_strategy_var.set(self._codex_strategy_label_for_id(self.session.codex_strategy.selected_preset_id))
        self.codex_mode_var.set(self._codex_mode_label_for_id(self.session.codex_strategy.selected_mode_id))
        self._set_scrolled_text(self.codex_strategy_note, self.session.codex_strategy.custom_instruction)
        self._load_policy_editors()

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

        self._refresh_control_center_header()
        self._refresh_project_home()
        self._refresh_codex_strategy_panel(self.session)
        self._refresh_popup_shell()

    def _collect_session(self) -> SessionConfig:
        session = SessionConfig.from_dict(self.session.to_dict())
        session.project.project_summary = self.project_summary.get("1.0", END).strip()
        session.project.target_outcome = self.target_outcome.get("1.0", END).strip()
        session.project.steps_text = self.steps_text.get("1.0", END).strip()
        session.codex_strategy.selected_preset_id = self._current_codex_strategy_preset_id()
        session.codex_strategy.selected_mode_id = self._current_codex_mode_id()
        session.codex_strategy.custom_instruction = self.codex_strategy_note.get("1.0", END).strip()

        sections, note = self._policy_input_snapshot()
        for section_key, _section_label, _section_description in POLICY_SECTION_SPECS:
            session.policy.set_section_text(section_key, sections.get(section_key, ""))
        session.policy.edit_note = note
        if self._policy_dirty:
            session.policy.last_edited_at = self._policy_live_edited_at or time.strftime("%Y-%m-%d %H:%M:%S")
            session.policy.last_edited_section = self._policy_last_edited_section or self._current_policy_section_key()
        session.project.operator_rules = session.policy.master_policy or session.policy.default_for("master_policy")

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
        persisted = self.store.save(self._build_persisted_state())
        self.session_schema_version = persisted.schema_version
        self.last_saved_at = persisted.saved_at
        self.log_reference_path = persisted.log_path
        self.recent_projects = persisted.recent_projects
        self._refresh_persistence_panel()
        self._refresh_policy_editor_state()

    def save_session(self) -> None:
        try:
            self.session = self._collect_session()
            self._save_session_quietly()
            self._policy_dirty = False
            self._policy_live_edited_at = ""
            self._policy_last_edited_section = self.session.policy.last_edited_section
            self._refresh_calibration_summary()
            self._refresh_prompt_panel_from_current_session()
            self._refresh_policy_editor_state()
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
        self._refresh_prompt_panel_from_current_session()
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
                f"{delay}초 안에 Codex 입력창 위에 마우스를 올려두세요. 시간이 지나면 현재 위치를 저장합니다."
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
            f"{remaining}초 뒤 현재 마우스 위치를 저장합니다. Codex 입력창 위에 마우스를 올려두세요."
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
            self.calibration_status_var.set(f"저장 완료: ({offset_x}, {offset_y}) @ {rect.width}x{rect.height}")
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
                "저장한 입력 위치를 클릭했습니다. "
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
                "안전 테스트 입력 완료: 메시지를 입력창에 붙여넣었지만 전송하지는 않았습니다."
            )
            self._refresh_runtime_labels()
            self._log(
                "안전 테스트 입력을 실행했습니다. "
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
            self._sync_prompt_draft_from_editor()
            report = self.engine.run_cycle(self.session, self.runtime)
            self._apply_report(report)
        except Exception as exc:
            messagebox.showerror("사이클 실행 실패", str(exc))

    def send_next_step(self) -> None:
        try:
            self.session = self._collect_session()
            self.runtime.clear_operator_pause()
            self._sync_prompt_draft_from_editor()
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
            self.runtime.clear_operator_pause()
            self._sync_prompt_draft_from_editor()
            self._save_session_quietly()
            self._refresh_calibration_summary()
            self._refresh_prompt_panel_from_current_session()
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
                for line in self._report_log_lines(report):
                    self.log_queue.put(line)
                self._needs_refresh = True
                self._needs_prompt_refresh = True
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
        for line in self._report_log_lines(report):
            self._log(line)
        self._refresh_prompt_panel_from_current_session()
        self._refresh_runtime_labels()

    def _format_report(self, report) -> str:
        parts = [report.message]
        if report.step_index is not None:
            step_label = report.step_title or "-"
            parts.append(f"단계: {report.step_index + 1} {step_label}")
        if report.window_title:
            parts.append(f"창: {report.window_title}")
        if report.lock_status:
            parts.append(f"타깃 상태: {report.lock_status}")
        if report.target_score is not None:
            parts.append(f"타깃 점수: {report.target_score}")
        if report.target_reason:
            parts.append(f"선택 근거: {report.target_reason}")
        if report.capture_path:
            parts.append(f"캡처: {report.capture_path}")
        if report.signature_distance is not None:
            parts.append(f"시그니처 거리: {report.signature_distance:.4f}")
        if report.step_sent:
            preview = report.step_sent.replace("\n", " ")[:160]
            source_text = "편집본" if report.prompt_source == "edited" else "원문"
            parts.append(f"프롬프트({source_text}): {preview}")
        return " | ".join(parts)

    def _format_prompt_audit(self, report) -> str | None:
        if not report.step_sent:
            return None

        lines = ["[프롬프트 기록]"]
        if report.step_index is not None:
            lines.append(f"단계: {report.step_index + 1} {report.step_title}")
        if report.prompt_source == "edited" and report.generated_prompt is not None:
            lines.extend(
                [
                    "원문:",
                    report.generated_prompt,
                    "",
                    "편집본:",
                    report.step_sent,
                ]
            )
        else:
            lines.extend(
                [
                    "전송 문구:",
                    report.step_sent,
                ]
            )
        return "\n".join(lines)

    def _report_log_lines(self, report) -> list[str]:
        lines = [self._format_report(report)]
        prompt_audit = self._format_prompt_audit(report)
        if prompt_audit:
            lines.append(prompt_audit)
        return lines

    def _refresh_calibration_summary(self) -> None:
        summary = self.session.automation.calibration_summary()
        delay = self.session.automation.calibration_delay_sec
        self.calibration_summary_var.set(f"{summary} | 딜레이 캡처 {delay}초")

    def _refresh_surface_state(self) -> None:
        self._surface_state = self.engine.build_surface_state(
            self.session,
            self.runtime,
            preview=self._current_preview,
            queue=self._current_queue,
        )

    def _refresh_popup_shell(self) -> None:
        self.popup_project_var.set(self._surface_state.project_label)
        self.popup_badge_var.set(self._surface_state.badge_label)
        self.popup_title_var.set(self._surface_state.title)
        self.popup_status_var.set(self._surface_state.summary)
        self.popup_reason_var.set(self._surface_state.reason)
        self.popup_next_action_var.set(self._surface_state.next_action)
        compact_hint = self._surface_state.next_action or self._surface_state.reason or self._surface_state.summary
        self.popup_compact_hint_var.set(compact_hint)
        self.popup_meta_var.set(self._surface_state.progress_label)
        self.popup_detail_var.set(self._surface_state.detail_label)
        self.popup_risk_var.set(f"위험 레벨 {self._surface_state.risk_label}")
        self._render_popup_actions()
        self._update_popup_density()

    def _refresh_runtime_labels(self) -> None:
        score_text = "없음" if self.runtime.last_target_score is None else str(self.runtime.last_target_score)
        self.next_step_label.config(text=f"다음 단계 인덱스: {self.runtime.next_step_index}")
        self.last_capture_label.config(text=f"마지막 캡처: {self.runtime.last_capture_path or '없음'}")
        self.auto_label.config(text=f"자동 루프: {'실행 중' if self.runtime.auto_running else '중지'}")
        self.target_window_label.config(text=f"타깃 창: {self.runtime.last_target_title or '없음'}")
        self.target_status_label.config(
            text=f"타깃 상태: {self.runtime.target_lock_status or '없음'} | 점수: {score_text}"
        )
        self.target_reason_label.config(text=f"선택 근거: {self.runtime.last_target_reason or '없음'}")
        self._refresh_surface_state()
        self._refresh_control_center_header()
        self._refresh_project_home()
        self._refresh_popup_shell()

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
        if self._needs_prompt_refresh:
            self._refresh_prompt_panel_from_current_session()
            self._needs_prompt_refresh = False
        self.root.after(250, self._pump_logs)

    def _log(self, message: str) -> None:
        clean_message = message.strip()
        self.store.append_log(clean_message)
        self.popup_last_event_var.set(clean_message)
        self.log_text.configure(state="normal")
        self.log_text.insert(END, clean_message + "\n")
        self.log_text.see(END)
        self.log_text.configure(state="disabled")


def launch_app() -> None:
    workspace = Path(__file__).resolve().parents[1]
    root = Tk()
    JavisApp(root, workspace)
    root.mainloop()
