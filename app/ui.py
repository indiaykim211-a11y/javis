from __future__ import annotations

import json
import queue
import threading
import time
import tkinter.font as tkfont
from pathlib import Path
from tkinter import BooleanVar, END, LEFT, StringVar, TclError, Tk, Toplevel, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from app.automation.windows_ui import WindowRect, WindowResolution, WindowsDesktopBridge
from app.models import (
    CODEX_AUTOMATION_MODE_OPTIONS,
    CODEX_AUTOMATION_PRESETS,
    DEEP_INTEGRATION_MODE_OPTIONS,
    DEEP_INTEGRATION_READINESS_OPTIONS,
    JUDGMENT_ENGINE_MODE_OPTIONS,
    LIVE_OPS_PROFILE_OPTIONS,
    LIVE_OPS_REENTRY_OPTIONS,
    LIVE_OPS_REPORT_CADENCE_OPTIONS,
    POLICY_SECTION_SPECS,
    VISUAL_CAPTURE_SCOPE_OPTIONS,
    VISUAL_RETENTION_OPTIONS,
    VISUAL_TARGET_MODE_OPTIONS,
    PersistedSessionState,
    PromptPreview,
    RuntimeState,
    SessionConfig,
    StepQueueItem,
    SurfaceStateModel,
    get_codex_automation_mode_option,
    get_deep_integration_mode_option,
    get_live_ops_profile_option,
)
from app.services.workflow import AutomationEngine
from app.state import SessionStore


class JavisApp:
    def __init__(self, root: Tk, workspace: Path) -> None:
        self.root = root
        self.root.title("javis")
        self._popup_expanded_size = (504, 520)
        self._popup_compact_size = (420, 292)
        self.root.geometry(f"{self._popup_expanded_size[0]}x{self._popup_expanded_size[1]}")
        self.root.minsize(392, 250)
        self.root.protocol("WM_DELETE_WINDOW", self._close_application)
        try:
            self.root.attributes("-topmost", True)
        except TclError:
            pass

        self._configure_design_system()

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
        self._current_deep_integration_registry = ""
        self._current_deep_integration_handoff = ""
        self._current_deep_integration_observability = ""
        self._current_live_ops_charter = ""
        self._current_live_ops_launchpad = ""
        self._current_live_ops_reentry_brief = ""
        self._current_live_ops_recovery = ""
        self._current_live_ops_shift_brief = ""
        self._current_judgment_packet = ""
        self._current_judgment_prompt = ""
        self._current_judgment_response = ""
        self._current_judgment_timeline = ""
        self._current_visual_packet = ""
        self._current_visual_prompt = ""
        self._current_visual_summary = ""
        self._current_visual_timeline = ""
        self._current_voice_result = ""
        self._current_voice_briefing = ""
        self._current_voice_timeline = ""

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

    def _pick_font_family(self, *candidates: str) -> str:
        families = set(tkfont.families(self.root))
        for candidate in candidates:
            if candidate in families:
                return candidate
        return "TkDefaultFont"

    def _configure_design_system(self) -> None:
        self._font_body = self._pick_font_family("맑은 고딕", "Malgun Gothic", "Segoe UI", "Arial")
        self._font_display = self._pick_font_family("Segoe UI", "맑은 고딕", "Malgun Gothic", "Arial")
        self._palette = {
            "bg": "#07111b",
            "panel": "#0c1b2a",
            "panel_soft": "#112538",
            "panel_alt": "#142f46",
            "panel_glow": "#183c58",
            "line": "#17364f",
            "line_strong": "#1ea7d7",
            "accent": "#6ce8ff",
            "accent_soft": "#3cc7f4",
            "accent_ice": "#baf6ff",
            "text": "#effaff",
            "muted": "#95b8c8",
            "muted_soft": "#6f95a7",
            "success": "#67f0c2",
            "warning": "#ffd071",
            "danger": "#ff8f8f",
        }
        self.root.configure(background=self._palette["bg"])
        self.root.option_add("*TCombobox*Listbox.font", (self._font_body, 10))
        self.root.option_add("*TCombobox*Listbox.background", self._palette["panel"])
        self.root.option_add("*TCombobox*Listbox.foreground", self._palette["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", self._palette["line_strong"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", self._palette["bg"])

    def _build_styles(self) -> None:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        bg = self._palette["bg"]
        panel = self._palette["panel"]
        panel_soft = self._palette["panel_soft"]
        panel_alt = self._palette["panel_alt"]
        panel_glow = self._palette["panel_glow"]
        line = self._palette["line"]
        line_strong = self._palette["line_strong"]
        accent = self._palette["accent"]
        accent_soft = self._palette["accent_soft"]
        accent_ice = self._palette["accent_ice"]
        text = self._palette["text"]
        muted = self._palette["muted"]
        muted_soft = self._palette["muted_soft"]

        style.configure(".", background=bg, foreground=text)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=text, font=(self._font_body, 10))
        style.configure("TLabelframe", background=bg, foreground=accent, borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", background=bg, foreground=accent, font=(self._font_body, 10, "bold"))
        style.configure("DeckRoot.TFrame", background=bg)
        style.configure("HeroBar.TFrame", background=panel_soft)
        style.configure("HeroInner.TFrame", background=panel_soft)
        style.configure("StatusStrip.TFrame", background=panel_alt)
        style.configure("Rail.TLabelframe", background=panel_soft, foreground=accent_ice, bordercolor=line_strong, borderwidth=1)
        style.configure("Rail.TLabelframe.Label", background=panel_soft, foreground=accent_ice, font=(self._font_body, 10, "bold"))
        style.configure("DeckCard.TLabelframe", background=panel_soft, foreground=accent_ice, bordercolor=line, borderwidth=1)
        style.configure("DeckCard.TLabelframe.Label", background=panel_soft, foreground=accent_ice, font=(self._font_body, 10, "bold"))
        style.configure("AccentCard.TLabelframe", background=panel_glow, foreground=accent_ice, bordercolor=line_strong, borderwidth=1)
        style.configure("AccentCard.TLabelframe.Label", background=panel_glow, foreground=accent_ice, font=(self._font_body, 10, "bold"))
        style.configure("HeroTitle.TLabel", background=panel_soft, foreground=accent_ice, font=(self._font_display, 20, "bold"))
        style.configure("HeroEyebrow.TLabel", background=panel_soft, foreground=accent_soft, font=(self._font_body, 9, "bold"))
        style.configure("HeroSub.TLabel", background=panel_soft, foreground=muted, font=(self._font_body, 9))
        style.configure("DeckTitle.TLabel", background=bg, foreground=accent_ice, font=(self._font_display, 18, "bold"))
        style.configure("DeckBody.TLabel", background=bg, foreground=muted, font=(self._font_body, 10))
        style.configure("StatValue.TLabel", background=panel_alt, foreground=text, font=(self._font_body, 13, "bold"))
        style.configure("StatCaption.TLabel", background=panel_alt, foreground=muted_soft, font=(self._font_body, 8))
        style.configure("RailNav.TButton", background=panel_soft, foreground=muted, bordercolor=panel_soft, focuscolor=line_strong, padding=(12, 10), font=(self._font_body, 10, "bold"))
        style.configure("RailNavActive.TButton", background=panel_glow, foreground=accent_ice, bordercolor=line_strong, focuscolor=accent, padding=(12, 10), font=(self._font_body, 10, "bold"))
        style.map(
            "RailNav.TButton",
            background=[("pressed", panel_alt), ("active", panel_alt)],
            foreground=[("pressed", text), ("active", text)],
            bordercolor=[("active", line)],
        )
        style.map(
            "RailNavActive.TButton",
            background=[("pressed", panel_glow), ("active", panel_glow)],
            foreground=[("pressed", accent_ice), ("active", accent_ice)],
            bordercolor=[("active", accent)],
        )
        style.configure(
            "TButton",
            background=panel,
            foreground=text,
            bordercolor=line,
            focuscolor=line_strong,
            lightcolor=line,
            darkcolor=line,
            padding=(10, 8),
            font=(self._font_body, 10),
        )
        style.map(
            "TButton",
            background=[("disabled", panel_soft), ("pressed", panel_soft), ("active", line)],
            foreground=[("disabled", muted), ("pressed", text), ("active", text)],
            bordercolor=[("active", line_strong)],
        )
        style.configure(
            "TEntry",
            fieldbackground=panel,
            foreground=text,
            insertcolor=accent,
            bordercolor=line,
            lightcolor=line,
            darkcolor=line,
            padding=6,
        )
        style.configure(
            "TCombobox",
            fieldbackground=panel,
            background=panel,
            foreground=text,
            arrowcolor=accent,
            bordercolor=line,
            lightcolor=line,
            darkcolor=line,
            padding=6,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", panel)],
            background=[("readonly", panel)],
            foreground=[("readonly", text)],
            arrowcolor=[("readonly", accent), ("active", accent_soft)],
        )
        style.configure("TCheckbutton", background=bg, foreground=text, font=(self._font_body, 10))
        style.map("TCheckbutton", background=[("active", bg)], foreground=[("disabled", muted)])
        style.configure("TNotebook", background=bg, borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure(
            "TNotebook.Tab",
            background=panel,
            foreground=muted,
            padding=(12, 8),
            font=(self._font_body, 10, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", panel_soft), ("active", panel_alt)],
            foreground=[("selected", accent), ("active", text)],
        )
        style.configure("Horizontal.TSeparator", background=line)

        style.configure("PopupShell.TFrame", background=bg, padding=22)
        style.configure("PopupTitle.TLabel", background=panel_soft, foreground=accent_ice, font=(self._font_display, 18, "bold"))
        style.configure("PopupProject.TLabel", background=bg, foreground=muted, font=(self._font_body, 9))
        style.configure(
            "PopupBadge.TLabel",
            background=panel_alt,
            foreground=accent_ice,
            font=(self._font_body, 9, "bold"),
            padding=(12, 5),
            borderwidth=1,
            relief="solid",
        )
        style.configure("PopupHeadline.TLabel", background=bg, foreground=text, font=(self._font_body, 15, "bold"))
        style.configure("PopupBody.TLabel", background=bg, foreground=text, font=(self._font_body, 10))
        style.configure("PopupMeta.TLabel", background=bg, foreground=muted, font=(self._font_body, 9))
        style.configure("PopupSection.TLabel", background=bg, foreground=accent_soft, font=(self._font_body, 9, "bold"))
        style.configure("AccentHeadline.TLabel", background=panel_glow, foreground=accent_ice, font=(self._font_body, 15, "bold"))
        style.configure("AccentBody.TLabel", background=panel_glow, foreground=text, font=(self._font_body, 10))
        style.configure("CardHeadline.TLabel", background=panel_soft, foreground=accent_ice, font=(self._font_body, 13, "bold"))
        style.configure("CardBody.TLabel", background=panel_soft, foreground=text, font=(self._font_body, 10))
        style.configure("CardMeta.TLabel", background=panel_soft, foreground=muted, font=(self._font_body, 9))
        style.configure("StripMeta.TLabel", background=panel_alt, foreground=muted, font=(self._font_body, 9))
        style.configure(
            "PopupPrimary.TButton",
            background=accent_soft,
            foreground=bg,
            bordercolor=accent_soft,
            focuscolor=accent,
            lightcolor=accent_soft,
            darkcolor=accent_soft,
            padding=(12, 10),
            font=(self._font_body, 10, "bold"),
        )
        style.map(
            "PopupPrimary.TButton",
            background=[("disabled", panel_soft), ("pressed", accent), ("active", accent)],
            foreground=[("disabled", muted), ("pressed", bg), ("active", bg)],
            bordercolor=[("active", accent)],
        )
        style.configure(
            "PopupSecondary.TButton",
            background=panel,
            foreground=text,
            bordercolor=line,
            focuscolor=line_strong,
            lightcolor=line,
            darkcolor=line,
            padding=(12, 10),
            font=(self._font_body, 10),
        )
        style.map(
            "PopupSecondary.TButton",
            background=[("disabled", panel_soft), ("pressed", panel_soft), ("active", line)],
            foreground=[("disabled", muted), ("pressed", text), ("active", text)],
            bordercolor=[("active", line_strong)],
        )

    def _apply_text_widget_theme(self, widget) -> None:
        if isinstance(widget, ScrolledText):
            state = str(widget.cget("state"))
            is_readonly = state == "disabled"
            widget.configure(
                font=(self._font_body, 10),
                background=self._palette["panel_soft"] if is_readonly else self._palette["panel"],
                foreground=self._palette["text"],
                insertbackground=self._palette["accent"],
                selectbackground=self._palette["line_strong"],
                selectforeground=self._palette["bg"],
                relief="flat",
                borderwidth=1,
                highlightthickness=1,
                highlightbackground=self._palette["line"],
                highlightcolor=self._palette["line_strong"],
                padx=10,
                pady=10,
            )
        for child in widget.winfo_children():
            self._apply_text_widget_theme(child)

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
        self.popup_eyebrow_var = StringVar(value="AUTONOMOUS CODEX OPERATOR")
        self.popup_subtitle_var = StringVar(value="핀테크급 운영 감각으로 현재 상태와 다음 행동을 요약합니다.")

        header = ttk.Frame(shell, style="HeroBar.TFrame", padding=14)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title_block = ttk.Frame(header, style="HeroInner.TFrame")
        title_block.grid(row=0, column=0, sticky="w")
        ttk.Label(title_block, textvariable=self.popup_eyebrow_var, style="HeroEyebrow.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(title_block, text="JAVIS // Live Ops", style="PopupTitle.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(title_block, textvariable=self.popup_subtitle_var, style="HeroSub.TLabel").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.popup_project_label = ttk.Label(title_block, textvariable=self.popup_project_var, style="HeroSub.TLabel")
        self.popup_project_label.grid(
            row=3, column=0, sticky="w", pady=(6, 0)
        )

        header_actions = ttk.Frame(header, style="HeroInner.TFrame")
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

        status_card = ttk.LabelFrame(body, text="지금 상태", padding=14, style="AccentCard.TLabelframe")
        status_card.grid(row=0, column=0, sticky="ew")
        status_card.columnconfigure(0, weight=1)
        ttk.Label(status_card, textvariable=self.popup_title_var, style="AccentHeadline.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.popup_status_label = ttk.Label(
            status_card,
            textvariable=self.popup_status_var,
            style="AccentBody.TLabel",
            wraplength=340,
            justify="left",
        )
        self.popup_status_label.grid(row=1, column=0, sticky="w", pady=(6, 0))

        self.popup_compact_frame = ttk.LabelFrame(body, text="한눈에 보기", padding=14, style="DeckCard.TLabelframe")
        self.popup_compact_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.popup_compact_frame.columnconfigure(0, weight=1)
        self.popup_compact_hint_label = ttk.Label(
            self.popup_compact_frame,
            textvariable=self.popup_compact_hint_var,
            style="CardBody.TLabel",
            wraplength=340,
            justify="left",
        )
        self.popup_compact_hint_label.grid(row=0, column=0, sticky="w")
        self.popup_compact_frame.grid_remove()

        self.popup_detail_frame = ttk.Frame(body)
        self.popup_detail_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.popup_detail_frame.columnconfigure(0, weight=1)

        reason_card = ttk.LabelFrame(self.popup_detail_frame, text="판단 이유", padding=14, style="DeckCard.TLabelframe")
        reason_card.grid(row=0, column=0, sticky="ew")
        reason_card.columnconfigure(0, weight=1)
        self.popup_reason_label = ttk.Label(
            reason_card,
            textvariable=self.popup_reason_var,
            style="CardBody.TLabel",
            wraplength=340,
            justify="left",
        )
        self.popup_reason_label.grid(row=0, column=0, sticky="w")

        next_card = ttk.LabelFrame(self.popup_detail_frame, text="추천 행동", padding=14, style="DeckCard.TLabelframe")
        next_card.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        next_card.columnconfigure(0, weight=1)
        self.popup_next_label = ttk.Label(
            next_card,
            textvariable=self.popup_next_action_var,
            style="CardBody.TLabel",
            wraplength=340,
            justify="left",
        )
        self.popup_next_label.grid(row=0, column=0, sticky="w")

        footer = ttk.Frame(body, style="StatusStrip.TFrame", padding=12)
        footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=1)
        self.popup_meta_label = ttk.Label(footer, textvariable=self.popup_meta_var, style="StripMeta.TLabel")
        self.popup_meta_label.grid(row=0, column=0, sticky="w")
        self.popup_risk_label = ttk.Label(footer, textvariable=self.popup_risk_var, style="StripMeta.TLabel")
        self.popup_risk_label.grid(row=0, column=1, sticky="e")
        self.popup_detail_label = ttk.Label(
            footer,
            textvariable=self.popup_detail_var,
            style="StripMeta.TLabel",
            wraplength=340,
            justify="left",
        )
        self.popup_detail_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.popup_last_event_label = ttk.Label(
            footer,
            textvariable=self.popup_last_event_var,
            style="StripMeta.TLabel",
            wraplength=340,
            justify="left",
        )
        self.popup_last_event_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.popup_footer_frame = footer

        action_bar = ttk.Frame(shell, style="HeroInner.TFrame")
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
        self.control_center.title("JAVIS // Control Deck")
        self.control_center.geometry("1320x960")
        self.control_center.configure(background=self._palette["bg"])
        self.control_center.transient(self.root)
        self.control_center.protocol("WM_DELETE_WINDOW", self.hide_control_center)
        self._build_control_center_layout(self.control_center)
        self._apply_text_widget_theme(self.control_center)

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
        self.deep_integration_mode_choice_by_label: dict[str, str] = {}
        self.deep_integration_mode_label_by_id: dict[str, str] = {}
        self.deep_integration_readiness_choice_by_label: dict[str, str] = {}
        self.deep_integration_readiness_label_by_id: dict[str, str] = {}
        self.live_ops_profile_choice_by_label: dict[str, str] = {}
        self.live_ops_profile_label_by_id: dict[str, str] = {}
        self.live_ops_report_choice_by_label: dict[str, str] = {}
        self.live_ops_report_label_by_id: dict[str, str] = {}
        self.live_ops_reentry_choice_by_label: dict[str, str] = {}
        self.live_ops_reentry_label_by_id: dict[str, str] = {}
        self.judgment_mode_choice_by_label: dict[str, str] = {}
        self.judgment_mode_label_by_id: dict[str, str] = {}
        self.visual_target_choice_by_label: dict[str, str] = {}
        self.visual_target_label_by_id: dict[str, str] = {}
        self.visual_scope_choice_by_label: dict[str, str] = {}
        self.visual_scope_label_by_id: dict[str, str] = {}
        self.visual_retention_choice_by_label: dict[str, str] = {}
        self.visual_retention_label_by_id: dict[str, str] = {}

        header = ttk.Frame(parent, style="HeroBar.TFrame", padding=16)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.columnconfigure(0, weight=1)

        title_block = ttk.Frame(header, style="HeroInner.TFrame")
        title_block.grid(row=0, column=0, sticky="w")
        ttk.Label(title_block, text="CONTROL DECK", style="HeroEyebrow.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(title_block, text="JAVIS // Control Deck", style="PopupTitle.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(
            title_block,
            textvariable=self.control_header_project_var,
            style="HeroSub.TLabel",
            wraplength=720,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Label(
            title_block,
            textvariable=self.control_header_status_var,
            style="HeroSub.TLabel",
            wraplength=720,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(4, 0))

        header_actions = ttk.Frame(header, style="HeroInner.TFrame")
        header_actions.grid(row=0, column=1, sticky="e")
        ttk.Button(header_actions, text="세션 저장", command=self.save_session).pack(side=LEFT, padx=(0, 8))
        ttk.Button(header_actions, text="팝업으로", command=self.hide_control_center).pack(side=LEFT, padx=(0, 8))
        ttk.Button(header_actions, text="닫기", command=self.hide_control_center).pack(side=LEFT)

        body = ttk.Frame(parent, style="DeckRoot.TFrame", padding=(14, 0, 14, 14))
        body.grid(row=1, column=0, columnspan=2, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        nav = ttk.LabelFrame(body, text="오퍼레이션 레일", padding=12, style="Rail.TLabelframe")
        nav.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        self.control_nav = nav

        content = ttk.Frame(body, style="DeckRoot.TFrame")
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
        model_voice_section = self._create_control_section("model_voice", "판단 / 모델 / 음성")
        visual_section = self._create_control_section("visual", "시각 감독")
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

        current_card = ttk.LabelFrame(home_frame, text="현재 프로젝트", padding=12, style="AccentCard.TLabelframe")
        current_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        current_card.columnconfigure(0, weight=1)

        ttk.Label(current_card, textvariable=self.project_home_title_var, style="AccentHeadline.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            current_card,
            textvariable=self.project_home_target_var,
            style="AccentBody.TLabel",
            wraplength=340,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(
            current_card,
            textvariable=self.project_home_strategy_var,
            style="AccentBody.TLabel",
            wraplength=340,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            current_card,
            textvariable=self.project_home_progress_var,
            style="AccentBody.TLabel",
            wraplength=340,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            current_card,
            textvariable=self.project_home_status_var,
            style="AccentBody.TLabel",
            wraplength=340,
            justify="left",
        ).grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            current_card,
            textvariable=self.project_home_capture_var,
            style="AccentBody.TLabel",
            wraplength=340,
            justify="left",
        ).grid(row=5, column=0, sticky="w", pady=(8, 0))
        ttk.Label(current_card, textvariable=self.schema_version_var, style="CardMeta.TLabel", wraplength=340, justify="left").grid(
            row=6, column=0, sticky="w", pady=(12, 0)
        )
        ttk.Label(current_card, textvariable=self.last_saved_var, style="CardMeta.TLabel", wraplength=340, justify="left").grid(
            row=7, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(current_card, textvariable=self.log_reference_var, style="CardMeta.TLabel", wraplength=340, justify="left").grid(
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

        recent_card = ttk.LabelFrame(home_frame, text="최근 프로젝트 / 이어가기", padding=12, style="DeckCard.TLabelframe")
        recent_card.grid(row=0, column=1, sticky="nsew")
        recent_card.columnconfigure(0, weight=1)

        self.recent_projects_combo = ttk.Combobox(recent_card, textvariable=self.recent_project_var, state="readonly")
        self.recent_projects_combo.grid(row=0, column=0, sticky="ew")
        self.recent_projects_combo.bind("<<ComboboxSelected>>", self._on_recent_project_selected)

        ttk.Label(
            recent_card,
            textvariable=self.recent_project_summary_var,
            style="CardHeadline.TLabel",
            wraplength=340,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Label(
            recent_card,
            textvariable=self.recent_project_target_var,
            style="CardBody.TLabel",
            wraplength=340,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            recent_card,
            textvariable=self.recent_project_strategy_var,
            style="CardBody.TLabel",
            wraplength=340,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            recent_card,
            textvariable=self.recent_project_progress_var,
            style="CardBody.TLabel",
            wraplength=340,
            justify="left",
        ).grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            recent_card,
            textvariable=self.recent_project_capture_var,
            style="CardMeta.TLabel",
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

        project_frame = ttk.LabelFrame(project_section, text="현재 프로젝트 편집", padding=12, style="DeckCard.TLabelframe")
        project_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        project_frame.columnconfigure(0, weight=1)

        ttk.Label(project_frame, text="프로젝트 요약").grid(row=0, column=0, sticky="w")
        self.project_summary = ScrolledText(project_frame, height=4, wrap="word")
        self.project_summary.grid(row=1, column=0, sticky="ew", pady=(4, 8))

        ttk.Label(project_frame, text="목표 수준").grid(row=2, column=0, sticky="w")
        self.target_outcome = ScrolledText(project_frame, height=4, wrap="word")
        self.target_outcome.grid(row=3, column=0, sticky="ew")

        steps_frame = ttk.LabelFrame(project_section, text="단계 목록", padding=12, style="DeckCard.TLabelframe")
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
        codex_strategy_section.rowconfigure(7, weight=1)
        codex_strategy_section.rowconfigure(8, weight=1)

        strategy_intro = ttk.LabelFrame(codex_strategy_section, text="Codex-first 안내", padding=12, style="AccentCard.TLabelframe")
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

        strategy_picker = ttk.LabelFrame(codex_strategy_section, text="운영 시나리오 선택", padding=12, style="DeckCard.TLabelframe")
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

        mode_frame = ttk.LabelFrame(codex_strategy_section, text="Automation mode 선택", padding=12, style="DeckCard.TLabelframe")
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

        recommended_frame = ttk.LabelFrame(strategy_body, text="추천 운영 정보", padding=12, style="DeckCard.TLabelframe")
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

        roles_frame = ttk.LabelFrame(strategy_body, text="역할 분리", padding=12, style="DeckCard.TLabelframe")
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

        strategy_note_frame = ttk.LabelFrame(codex_strategy_section, text="추가 지시 / follow-up 메모", padding=12, style="DeckCard.TLabelframe")
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

        strategy_prompt_frame = ttk.LabelFrame(codex_strategy_section, text="Launch-ready Prompt 초안", padding=12, style="AccentCard.TLabelframe")
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

        runbook_frame = ttk.LabelFrame(strategy_bottom, text="Launch Checklist / Handoff", padding=12, style="DeckCard.TLabelframe")
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

        runboard_frame = ttk.LabelFrame(strategy_bottom, text="Automation Runboard", padding=12, style="DeckCard.TLabelframe")
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

        triage_frame = ttk.LabelFrame(strategy_bottom, text="Triage / Re-entry Bridge", padding=12, style="DeckCard.TLabelframe")
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

        matrix_frame = ttk.LabelFrame(strategy_bottom, text="Safety Guard / Native vs Fallback", padding=12, style="DeckCard.TLabelframe")
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

        deep_integration_frame = ttk.LabelFrame(codex_strategy_section, text="Deep Integration", padding=12, style="DeckCard.TLabelframe")
        deep_integration_frame.grid(row=7, column=0, sticky="nsew", pady=(12, 0))
        deep_integration_frame.columnconfigure(0, weight=1)
        deep_integration_frame.rowconfigure(3, weight=1)

        deep_controls = ttk.Frame(deep_integration_frame)
        deep_controls.grid(row=0, column=0, sticky="ew")
        deep_controls.columnconfigure(1, weight=1)
        deep_controls.columnconfigure(3, weight=1)

        self.deep_integration_mode_var = StringVar()
        for option in DEEP_INTEGRATION_MODE_OPTIONS:
            self.deep_integration_mode_choice_by_label[option.title] = option.mode_id
            self.deep_integration_mode_label_by_id[option.mode_id] = option.title

        self.deep_app_server_readiness_var = StringVar()
        self.deep_cloud_trigger_readiness_var = StringVar()
        for option in DEEP_INTEGRATION_READINESS_OPTIONS:
            self.deep_integration_readiness_choice_by_label[option.title] = option.readiness_id
            self.deep_integration_readiness_label_by_id[option.readiness_id] = option.title

        self.deep_fallback_allowed_var = BooleanVar(value=self.session.deep_integration.desktop_fallback_allowed)
        self.deep_app_server_notes_var = StringVar(value=self.session.deep_integration.app_server_notes)
        self.deep_cloud_trigger_notes_var = StringVar(value=self.session.deep_integration.cloud_trigger_notes)

        ttk.Label(deep_controls, text="integration mode").grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.deep_integration_mode_combo = ttk.Combobox(
            deep_controls,
            textvariable=self.deep_integration_mode_var,
            state="readonly",
            values=list(self.deep_integration_mode_choice_by_label.keys()),
        )
        self.deep_integration_mode_combo.grid(row=0, column=1, sticky="ew")
        self.deep_integration_mode_combo.bind("<<ComboboxSelected>>", self._on_deep_integration_settings_changed)

        ttk.Label(deep_controls, text="App Server readiness").grid(row=0, column=2, sticky="w", padx=(16, 12))
        self.deep_app_server_readiness_combo = ttk.Combobox(
            deep_controls,
            textvariable=self.deep_app_server_readiness_var,
            state="readonly",
            values=list(self.deep_integration_readiness_choice_by_label.keys()),
        )
        self.deep_app_server_readiness_combo.grid(row=0, column=3, sticky="ew")
        self.deep_app_server_readiness_combo.bind("<<ComboboxSelected>>", self._on_deep_integration_settings_changed)

        ttk.Label(deep_controls, text="Cloud Trigger readiness").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(10, 0))
        self.deep_cloud_trigger_readiness_combo = ttk.Combobox(
            deep_controls,
            textvariable=self.deep_cloud_trigger_readiness_var,
            state="readonly",
            values=list(self.deep_integration_readiness_choice_by_label.keys()),
        )
        self.deep_cloud_trigger_readiness_combo.grid(row=1, column=1, sticky="ew", pady=(10, 0))
        self.deep_cloud_trigger_readiness_combo.bind("<<ComboboxSelected>>", self._on_deep_integration_settings_changed)

        ttk.Label(deep_controls, text="App Server 메모").grid(row=1, column=2, sticky="w", padx=(16, 12), pady=(10, 0))
        ttk.Entry(deep_controls, textvariable=self.deep_app_server_notes_var).grid(row=1, column=3, sticky="ew", pady=(10, 0))

        ttk.Label(deep_controls, text="Cloud 메모").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=(10, 0))
        ttk.Entry(deep_controls, textvariable=self.deep_cloud_trigger_notes_var).grid(row=2, column=1, sticky="ew", pady=(10, 0))
        ttk.Checkbutton(
            deep_controls,
            text="desktop fallback 허용",
            variable=self.deep_fallback_allowed_var,
            command=self._on_deep_integration_settings_changed,
        ).grid(row=2, column=2, columnspan=2, sticky="w", pady=(10, 0))

        deep_actions = ttk.Frame(deep_integration_frame)
        deep_actions.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        for index, (label, command) in enumerate(
            [
                ("Deep 새로고침", self.refresh_deep_integration_panel_now),
                ("Capability 복사", self.copy_deep_integration_registry),
                ("Handoff 복사", self.copy_deep_integration_handoff),
                ("Observability 복사", self.copy_deep_integration_observability),
            ]
        ):
            ttk.Button(deep_actions, text=label, command=command).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, 8 if index < 3 else 0),
            )
            deep_actions.columnconfigure(index, weight=1)

        self.deep_integration_mode_status_var = StringVar(value="deep integration 추천 mode가 여기에 표시됩니다.")
        self.deep_integration_supervisor_var = StringVar(value="supervisor state가 여기에 표시됩니다.")
        self.deep_integration_fallback_var = StringVar(value="fallback 상태가 여기에 표시됩니다.")
        self.deep_integration_reentry_var = StringVar(value="handoff target과 re-entry source가 여기에 표시됩니다.")

        deep_status = ttk.LabelFrame(deep_integration_frame, text="현재 Deep Integration 상태", padding=12)
        deep_status.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        deep_status.columnconfigure(0, weight=1)
        ttk.Label(deep_status, textvariable=self.deep_integration_mode_status_var, wraplength=760, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(deep_status, textvariable=self.deep_integration_supervisor_var, wraplength=760, justify="left").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(deep_status, textvariable=self.deep_integration_fallback_var, wraplength=760, justify="left").grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(deep_status, textvariable=self.deep_integration_reentry_var, wraplength=760, justify="left").grid(
            row=3, column=0, sticky="w", pady=(4, 0)
        )

        deep_body = ttk.Frame(deep_integration_frame)
        deep_body.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        deep_body.columnconfigure(0, weight=1)
        deep_body.columnconfigure(1, weight=1)
        deep_body.rowconfigure(0, weight=1)
        deep_body.rowconfigure(1, weight=1)

        deep_registry_frame = ttk.LabelFrame(deep_body, text="Capability Registry", padding=12)
        deep_registry_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        deep_registry_frame.columnconfigure(0, weight=1)
        deep_registry_frame.rowconfigure(1, weight=1)
        self.deep_integration_registry_state_var = StringVar(value="현재 환경의 capability registry가 여기에 표시됩니다.")
        ttk.Label(deep_registry_frame, textvariable=self.deep_integration_registry_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.deep_integration_registry_preview = ScrolledText(deep_registry_frame, height=10, wrap="word", state="disabled")
        self.deep_integration_registry_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        deep_observability_frame = ttk.LabelFrame(deep_body, text="Integration Observability", padding=12)
        deep_observability_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        deep_observability_frame.columnconfigure(0, weight=1)
        deep_observability_frame.rowconfigure(1, weight=1)
        self.deep_integration_observability_state_var = StringVar(value="현재 mode, supervisor, fallback 상태가 여기에 표시됩니다.")
        ttk.Label(
            deep_observability_frame,
            textvariable=self.deep_integration_observability_state_var,
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.deep_integration_observability_preview = ScrolledText(
            deep_observability_frame,
            height=10,
            wrap="word",
            state="disabled",
        )
        self.deep_integration_observability_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        deep_handoff_frame = ttk.LabelFrame(deep_body, text="Cross-Surface Handoff", padding=12)
        deep_handoff_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        deep_handoff_frame.columnconfigure(0, weight=1)
        deep_handoff_frame.rowconfigure(1, weight=1)
        self.deep_integration_handoff_state_var = StringVar(value="popup / Control Center / triage / voice를 잇는 handoff bundle이 여기에 표시됩니다.")
        ttk.Label(deep_handoff_frame, textvariable=self.deep_integration_handoff_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.deep_integration_handoff_preview = ScrolledText(deep_handoff_frame, height=10, wrap="word", state="disabled")
        self.deep_integration_handoff_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        deep_notes_frame = ttk.LabelFrame(deep_body, text="Handoff Notes", padding=12)
        deep_notes_frame.grid(row=1, column=1, sticky="nsew")
        deep_notes_frame.columnconfigure(0, weight=1)
        deep_notes_frame.rowconfigure(1, weight=1)
        ttk.Label(
            deep_notes_frame,
            text="App Server, cloud trigger, fallback 진입/해제 기준에 대한 운영 메모를 적어둘 수 있습니다.",
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.deep_handoff_note = ScrolledText(deep_notes_frame, height=10, wrap="word")
        self.deep_handoff_note.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        live_ops_frame = ttk.LabelFrame(codex_strategy_section, text="라이브 오퍼레이션", padding=12, style="AccentCard.TLabelframe")
        live_ops_frame.grid(row=8, column=0, sticky="nsew", pady=(12, 0))
        live_ops_frame.columnconfigure(0, weight=1)
        live_ops_frame.rowconfigure(3, weight=1)

        live_controls = ttk.Frame(live_ops_frame)
        live_controls.grid(row=0, column=0, sticky="ew")
        live_controls.columnconfigure(1, weight=1)
        live_controls.columnconfigure(3, weight=1)

        self.live_ops_profile_var = StringVar()
        for option in LIVE_OPS_PROFILE_OPTIONS:
            self.live_ops_profile_choice_by_label[option.title] = option.profile_id
            self.live_ops_profile_label_by_id[option.profile_id] = option.title

        self.live_ops_report_var = StringVar()
        for option in LIVE_OPS_REPORT_CADENCE_OPTIONS:
            self.live_ops_report_choice_by_label[option.title] = option.cadence_id
            self.live_ops_report_label_by_id[option.cadence_id] = option.title

        self.live_ops_reentry_var = StringVar()
        for option in LIVE_OPS_REENTRY_OPTIONS:
            self.live_ops_reentry_choice_by_label[option.title] = option.reentry_id
            self.live_ops_reentry_label_by_id[option.reentry_id] = option.title

        self.live_ops_max_steps_var = StringVar(value=str(self.session.live_ops.max_unattended_steps))

        ttk.Label(live_controls, text="운영 프로필").grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.live_ops_profile_combo = ttk.Combobox(
            live_controls,
            textvariable=self.live_ops_profile_var,
            state="readonly",
            values=list(self.live_ops_profile_choice_by_label.keys()),
        )
        self.live_ops_profile_combo.grid(row=0, column=1, sticky="ew")
        self.live_ops_profile_combo.bind("<<ComboboxSelected>>", self._on_live_ops_settings_changed)

        ttk.Label(live_controls, text="보고 주기").grid(row=0, column=2, sticky="w", padx=(16, 12))
        self.live_ops_report_combo = ttk.Combobox(
            live_controls,
            textvariable=self.live_ops_report_var,
            state="readonly",
            values=list(self.live_ops_report_choice_by_label.keys()),
        )
        self.live_ops_report_combo.grid(row=0, column=3, sticky="ew")
        self.live_ops_report_combo.bind("<<ComboboxSelected>>", self._on_live_ops_settings_changed)

        ttk.Label(live_controls, text="재진입 방식").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(10, 0))
        self.live_ops_reentry_combo = ttk.Combobox(
            live_controls,
            textvariable=self.live_ops_reentry_var,
            state="readonly",
            values=list(self.live_ops_reentry_choice_by_label.keys()),
        )
        self.live_ops_reentry_combo.grid(row=1, column=1, sticky="ew", pady=(10, 0))
        self.live_ops_reentry_combo.bind("<<ComboboxSelected>>", self._on_live_ops_settings_changed)

        ttk.Label(live_controls, text="무인 진행 단계 수").grid(row=1, column=2, sticky="w", padx=(16, 12), pady=(10, 0))
        ttk.Entry(live_controls, textvariable=self.live_ops_max_steps_var).grid(row=1, column=3, sticky="ew", pady=(10, 0))

        live_actions = ttk.Frame(live_ops_frame)
        live_actions.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        for index, (label, command) in enumerate(
            [
                ("운영 새로고침", self.refresh_live_ops_panel_now),
                ("차터 복사", self.copy_live_ops_charter),
                ("재진입 복사", self.copy_live_ops_reentry_brief),
                ("복구안 복사", self.copy_live_ops_recovery),
                ("브리프 복사", self.copy_live_ops_shift_brief),
            ]
        ):
            ttk.Button(live_actions, text=label, command=command).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, 8 if index < 4 else 0),
            )
            live_actions.columnconfigure(index, weight=1)

        self.live_ops_profile_status_var = StringVar(value="운영 프로필과 보고 주기 상태가 여기에 표시됩니다.")
        self.live_ops_lane_status_var = StringVar(value="현재 운영 레인이 여기에 표시됩니다.")
        self.live_ops_touchpoint_var = StringVar(value="다음 터치포인트가 여기에 표시됩니다.")
        self.live_ops_recovery_status_var = StringVar(value="현재 복구 수준과 이유가 여기에 표시됩니다.")

        live_status = ttk.LabelFrame(live_ops_frame, text="현재 운영 상태", padding=12)
        live_status.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        live_status.columnconfigure(0, weight=1)
        ttk.Label(live_status, textvariable=self.live_ops_profile_status_var, wraplength=760, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(live_status, textvariable=self.live_ops_lane_status_var, wraplength=760, justify="left").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(live_status, textvariable=self.live_ops_touchpoint_var, wraplength=760, justify="left").grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(live_status, textvariable=self.live_ops_recovery_status_var, wraplength=760, justify="left").grid(
            row=3, column=0, sticky="w", pady=(4, 0)
        )

        live_body = ttk.Frame(live_ops_frame)
        live_body.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        live_body.columnconfigure(0, weight=1)
        live_body.columnconfigure(1, weight=1)
        live_body.rowconfigure(0, weight=1)
        live_body.rowconfigure(1, weight=1)
        live_body.rowconfigure(2, weight=1)

        live_charter_frame = ttk.LabelFrame(live_body, text="운영 차터", padding=12)
        live_charter_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        live_charter_frame.columnconfigure(0, weight=1)
        live_charter_frame.rowconfigure(1, weight=1)
        self.live_ops_charter_state_var = StringVar(value="운영 원칙과 감독 가드가 여기에 표시됩니다.")
        ttk.Label(live_charter_frame, textvariable=self.live_ops_charter_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.live_ops_charter_preview = ScrolledText(live_charter_frame, height=10, wrap="word", state="disabled")
        self.live_ops_charter_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        live_launchpad_frame = ttk.LabelFrame(live_body, text="런치패드", padding=12)
        live_launchpad_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        live_launchpad_frame.columnconfigure(0, weight=1)
        live_launchpad_frame.rowconfigure(1, weight=1)
        self.live_ops_launchpad_state_var = StringVar(value="지금 확인할 체크리스트와 즉시 행동이 여기에 표시됩니다.")
        ttk.Label(live_launchpad_frame, textvariable=self.live_ops_launchpad_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.live_ops_launchpad_preview = ScrolledText(live_launchpad_frame, height=10, wrap="word", state="disabled")
        self.live_ops_launchpad_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        live_reentry_frame = ttk.LabelFrame(live_body, text="재진입 브리프", padding=12)
        live_reentry_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        live_reentry_frame.columnconfigure(0, weight=1)
        live_reentry_frame.rowconfigure(1, weight=1)
        self.live_ops_reentry_state_var = StringVar(value="현재 결과를 다시 읽고 운영 스레드로 들어오는 기준이 여기에 표시됩니다.")
        ttk.Label(live_reentry_frame, textvariable=self.live_ops_reentry_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.live_ops_reentry_preview = ScrolledText(live_reentry_frame, height=10, wrap="word", state="disabled")
        self.live_ops_reentry_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        live_recovery_frame = ttk.LabelFrame(live_body, text="복구 플레이북", padding=12)
        live_recovery_frame.grid(row=1, column=1, sticky="nsew", pady=(0, 8))
        live_recovery_frame.columnconfigure(0, weight=1)
        live_recovery_frame.rowconfigure(1, weight=1)
        self.live_ops_recovery_state_var = StringVar(value="막혔을 때 어떤 수준으로 복구할지 여기에 표시됩니다.")
        ttk.Label(live_recovery_frame, textvariable=self.live_ops_recovery_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.live_ops_recovery_preview = ScrolledText(live_recovery_frame, height=10, wrap="word", state="disabled")
        self.live_ops_recovery_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        live_shift_frame = ttk.LabelFrame(live_body, text="시프트 브리프", padding=12)
        live_shift_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
        live_shift_frame.columnconfigure(0, weight=1)
        live_shift_frame.rowconfigure(1, weight=1)
        self.live_ops_shift_state_var = StringVar(value="현재 운영 상태를 운영자 시점으로 짧게 요약해 보여줍니다.")
        ttk.Label(live_shift_frame, textvariable=self.live_ops_shift_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.live_ops_shift_preview = ScrolledText(live_shift_frame, height=10, wrap="word", state="disabled")
        self.live_ops_shift_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        live_note_frame = ttk.LabelFrame(live_body, text="운영 메모", padding=12)
        live_note_frame.grid(row=2, column=1, sticky="nsew")
        live_note_frame.columnconfigure(0, weight=1)
        live_note_frame.rowconfigure(1, weight=1)
        ttk.Label(
            live_note_frame,
            text="실제 운영에서 꼭 지키고 싶은 감독 규칙이나 handoff 취향을 적어둘 수 있습니다.",
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.live_ops_note = ScrolledText(live_note_frame, height=10, wrap="word")
        self.live_ops_note.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

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
        model_voice_section.rowconfigure(3, weight=1)
        model_voice_section.rowconfigure(6, weight=1)

        judgment_intro = ttk.LabelFrame(model_voice_section, text="Judgment Overlay 안내", padding=12)
        judgment_intro.grid(row=0, column=0, sticky="ew")
        judgment_intro.columnconfigure(0, weight=1)
        ttk.Label(
            judgment_intro,
            text=(
                "Phase 4에서는 OpenAI-ready 판단 엔진을 제품 안에 먼저 붙입니다. "
                "현재는 안전한 규칙 기반 판단을 기본으로 두고, 준비가 되면 OpenAI 판단으로 확장할 수 있게 설계합니다."
            ),
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        judgment_settings = ttk.LabelFrame(model_voice_section, text="판단 엔진 설정", padding=12)
        judgment_settings.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        judgment_settings.columnconfigure(1, weight=1)
        judgment_settings.columnconfigure(3, weight=1)

        self.judgment_engine_mode_var = StringVar()
        self.judgment_model_name_var = StringVar(value=self.session.judgment.model_name)
        self.judgment_confidence_var = StringVar(value=str(self.session.judgment.confidence_threshold))
        for option in JUDGMENT_ENGINE_MODE_OPTIONS:
            self.judgment_mode_choice_by_label[option.title] = option.mode_id
            self.judgment_mode_label_by_id[option.mode_id] = option.title

        ttk.Label(judgment_settings, text="엔진 모드").grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.judgment_engine_combo = ttk.Combobox(
            judgment_settings,
            textvariable=self.judgment_engine_mode_var,
            state="readonly",
            values=list(self.judgment_mode_choice_by_label.keys()),
        )
        self.judgment_engine_combo.grid(row=0, column=1, sticky="ew")
        self.judgment_engine_combo.bind("<<ComboboxSelected>>", self._on_judgment_engine_mode_selected)

        ttk.Label(judgment_settings, text="모델 이름").grid(row=0, column=2, sticky="w", padx=(16, 12))
        ttk.Entry(judgment_settings, textvariable=self.judgment_model_name_var).grid(row=0, column=3, sticky="ew")

        ttk.Label(judgment_settings, text="confidence threshold").grid(row=1, column=0, sticky="w", pady=(10, 0), padx=(0, 12))
        ttk.Entry(judgment_settings, textvariable=self.judgment_confidence_var).grid(
            row=1, column=1, sticky="ew", pady=(10, 0)
        )

        judgment_actions = ttk.Frame(judgment_settings)
        judgment_actions.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        for index, (label, command) in enumerate(
            [
                ("재판단 실행", self.run_judgment_now),
                ("패킷 복사", self.copy_judgment_packet),
                ("프롬프트 복사", self.copy_judgment_prompt),
                ("응답 복사", self.copy_judgment_response),
                ("타임라인 복사", self.copy_judgment_timeline),
            ]
        ):
            ttk.Button(judgment_actions, text=label, command=command).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, 8 if index < 4 else 0),
            )
            judgment_actions.columnconfigure(index, weight=1)

        judgment_status = ttk.LabelFrame(model_voice_section, text="현재 판단 상태", padding=12)
        judgment_status.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        judgment_status.columnconfigure(0, weight=1)
        self.judgment_engine_status_var = StringVar(value="판단 엔진 상태를 불러오는 중입니다.")
        self.judgment_result_status_var = StringVar(value="아직 판단 결과가 없습니다.")
        self.judgment_source_status_var = StringVar(value="source / confidence / risk 정보가 여기에 표시됩니다.")
        self.judgment_follow_up_var = StringVar(value="후속 행동 요약이 여기에 표시됩니다.")
        ttk.Label(judgment_status, textvariable=self.judgment_engine_status_var, wraplength=760, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(judgment_status, textvariable=self.judgment_result_status_var, wraplength=760, justify="left").grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Label(judgment_status, textvariable=self.judgment_source_status_var, wraplength=760, justify="left").grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Label(judgment_status, textvariable=self.judgment_follow_up_var, wraplength=760, justify="left").grid(
            row=3, column=0, sticky="w", pady=(6, 0)
        )

        judgment_body = ttk.Frame(model_voice_section)
        judgment_body.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        judgment_body.columnconfigure(0, weight=1)
        judgment_body.columnconfigure(1, weight=1)
        judgment_body.rowconfigure(0, weight=1)
        judgment_body.rowconfigure(1, weight=1)

        packet_frame = ttk.LabelFrame(judgment_body, text="Judgment Packet", padding=12)
        packet_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        packet_frame.columnconfigure(0, weight=1)
        packet_frame.rowconfigure(1, weight=1)
        self.judgment_packet_state_var = StringVar(value="판단 입력 패킷 초안이 여기에 표시됩니다.")
        ttk.Label(packet_frame, textvariable=self.judgment_packet_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.judgment_packet_preview = ScrolledText(packet_frame, height=12, wrap="word", state="disabled")
        self.judgment_packet_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        prompt_frame = ttk.LabelFrame(judgment_body, text="Judgment Prompt", padding=12)
        prompt_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(1, weight=1)
        self.judgment_prompt_state_var = StringVar(value="판단 프롬프트 초안이 여기에 표시됩니다.")
        ttk.Label(prompt_frame, textvariable=self.judgment_prompt_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.judgment_prompt_preview = ScrolledText(prompt_frame, height=12, wrap="word", state="disabled")
        self.judgment_prompt_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        response_frame = ttk.LabelFrame(judgment_body, text="Validated Response", padding=12)
        response_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        response_frame.columnconfigure(0, weight=1)
        response_frame.rowconfigure(1, weight=1)
        self.judgment_response_state_var = StringVar(value="검증된 판단 응답이 여기에 표시됩니다.")
        ttk.Label(response_frame, textvariable=self.judgment_response_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.judgment_response_preview = ScrolledText(response_frame, height=12, wrap="word", state="disabled")
        self.judgment_response_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        timeline_frame = ttk.LabelFrame(judgment_body, text="Timeline / Evidence Digest", padding=12)
        timeline_frame.grid(row=1, column=1, sticky="nsew")
        timeline_frame.columnconfigure(0, weight=1)
        timeline_frame.rowconfigure(1, weight=1)
        self.judgment_timeline_state_var = StringVar(value="최근 판단 이력과 근거 요약이 여기에 표시됩니다.")
        ttk.Label(timeline_frame, textvariable=self.judgment_timeline_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.judgment_timeline_preview = ScrolledText(timeline_frame, height=12, wrap="word", state="disabled")
        self.judgment_timeline_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        voice_intro = ttk.LabelFrame(model_voice_section, text="Voice Assistant 안내", padding=12)
        voice_intro.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        voice_intro.columnconfigure(0, weight=1)
        ttk.Label(
            voice_intro,
            text=(
                "Phase 6에서는 voice를 새 판단 엔진으로 만들지 않고, 기존 judgment / visual 흐름을 "
                "말로 더 쉽게 쓰는 상위 인터페이스로 올립니다. 지금 단계에서는 push-to-talk, "
                "transcript 정규화, spoken briefing, confirmation gate를 먼저 붙입니다."
            ),
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        voice_settings = ttk.LabelFrame(model_voice_section, text="음성 설정", padding=12)
        voice_settings.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        voice_settings.columnconfigure(1, weight=1)
        voice_settings.columnconfigure(3, weight=1)

        self.voice_language_var = StringVar(value=self.session.voice.language_code)
        self.voice_microphone_var = StringVar(value=self.session.voice.microphone_name)
        self.voice_speaker_var = StringVar(value=self.session.voice.speaker_name)
        self.voice_auto_brief_var = BooleanVar(value=self.session.voice.auto_brief_enabled)
        self.voice_confirmation_var = BooleanVar(value=self.session.voice.confirmation_enabled)
        self.voice_spoken_feedback_var = BooleanVar(value=self.session.voice.spoken_feedback_enabled)
        self.voice_ambient_ready_var = BooleanVar(value=self.session.voice.ambient_ready_enabled)

        ttk.Label(voice_settings, text="언어 코드").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Entry(voice_settings, textvariable=self.voice_language_var).grid(row=0, column=1, sticky="ew")
        ttk.Label(voice_settings, text="마이크").grid(row=0, column=2, sticky="w", padx=(16, 12))
        ttk.Entry(voice_settings, textvariable=self.voice_microphone_var).grid(row=0, column=3, sticky="ew")

        ttk.Label(voice_settings, text="스피커").grid(row=1, column=0, sticky="w", pady=(10, 0), padx=(0, 12))
        ttk.Entry(voice_settings, textvariable=self.voice_speaker_var).grid(row=1, column=1, sticky="ew", pady=(10, 0))

        voice_toggle_row = ttk.Frame(voice_settings)
        voice_toggle_row.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        for index, (label, variable) in enumerate(
            [
                ("자동 브리핑", self.voice_auto_brief_var),
                ("확인 게이트", self.voice_confirmation_var),
                ("spoken feedback", self.voice_spoken_feedback_var),
                ("ambient ready", self.voice_ambient_ready_var),
            ]
        ):
            ttk.Checkbutton(voice_toggle_row, text=label, variable=variable).grid(
                row=0,
                column=index,
                sticky="w",
                padx=(0, 12 if index < 3 else 0),
            )
            voice_toggle_row.columnconfigure(index, weight=1)

        voice_status = ttk.LabelFrame(model_voice_section, text="현재 음성 상태", padding=12)
        voice_status.grid(row=6, column=0, sticky="ew", pady=(12, 0))
        voice_status.columnconfigure(0, weight=1)
        self.voice_capture_status_var = StringVar(value="voice capture 상태가 여기 표시됩니다.")
        self.voice_result_status_var = StringVar(value="아직 voice intent 결과가 없습니다.")
        self.voice_confirmation_status_var = StringVar(value="대기 중인 voice confirmation이 없습니다.")
        ttk.Label(voice_status, textvariable=self.voice_capture_status_var, wraplength=760, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(voice_status, textvariable=self.voice_result_status_var, wraplength=760, justify="left").grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Label(
            voice_status,
            textvariable=self.voice_confirmation_status_var,
            wraplength=760,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(6, 0))

        voice_body = ttk.Frame(model_voice_section)
        voice_body.grid(row=7, column=0, sticky="nsew", pady=(12, 0))
        voice_body.columnconfigure(0, weight=1)
        voice_body.columnconfigure(1, weight=1)
        voice_body.rowconfigure(0, weight=1)
        voice_body.rowconfigure(1, weight=1)

        voice_input_frame = ttk.LabelFrame(voice_body, text="Push-to-Talk / Transcript", padding=12)
        voice_input_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        voice_input_frame.columnconfigure(0, weight=1)
        voice_input_frame.rowconfigure(1, weight=1)
        ttk.Label(
            voice_input_frame,
            text="push-to-talk 버튼으로 상태를 바꾸고, 현재 단계에서는 transcript를 직접 점검 / 수정할 수 있습니다.",
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.voice_transcript_input = ScrolledText(voice_input_frame, height=10, wrap="word")
        self.voice_transcript_input.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        voice_actions = ttk.Frame(voice_input_frame)
        voice_actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for index, (label, command) in enumerate(
            [
                ("push-to-talk", self.toggle_voice_capture),
                ("voice 실행", self.run_voice_command_now),
                ("브리핑 읽기", self.play_voice_briefing_now),
                ("확인", self.confirm_pending_voice_action),
                ("취소", self.cancel_pending_voice_action),
            ]
        ):
            ttk.Button(voice_actions, text=label, command=command).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, 8 if index < 4 else 0),
            )
            voice_actions.columnconfigure(index, weight=1)

        voice_result_frame = ttk.LabelFrame(voice_body, text="Voice Intent Result", padding=12)
        voice_result_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        voice_result_frame.columnconfigure(0, weight=1)
        voice_result_frame.rowconfigure(1, weight=1)
        self.voice_result_state_var = StringVar(value="voice intent 결과가 여기 표시됩니다.")
        ttk.Label(voice_result_frame, textvariable=self.voice_result_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.voice_result_preview = ScrolledText(voice_result_frame, height=10, wrap="word", state="disabled")
        self.voice_result_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        voice_briefing_frame = ttk.LabelFrame(voice_body, text="Spoken Briefing", padding=12)
        voice_briefing_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        voice_briefing_frame.columnconfigure(0, weight=1)
        voice_briefing_frame.rowconfigure(1, weight=1)
        self.voice_briefing_state_var = StringVar(value="spoken briefing 초안이 여기 표시됩니다.")
        ttk.Label(
            voice_briefing_frame,
            textvariable=self.voice_briefing_state_var,
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.voice_briefing_preview = ScrolledText(voice_briefing_frame, height=10, wrap="word", state="disabled")
        self.voice_briefing_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        voice_timeline_frame = ttk.LabelFrame(voice_body, text="Voice Timeline / Guard", padding=12)
        voice_timeline_frame.grid(row=1, column=1, sticky="nsew")
        voice_timeline_frame.columnconfigure(0, weight=1)
        voice_timeline_frame.rowconfigure(1, weight=1)
        self.voice_timeline_state_var = StringVar(value="voice history와 confirmation 상태가 여기 표시됩니다.")
        ttk.Label(
            voice_timeline_frame,
            textvariable=self.voice_timeline_state_var,
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.voice_timeline_preview = ScrolledText(voice_timeline_frame, height=10, wrap="word", state="disabled")
        self.voice_timeline_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        voice_copy_actions = ttk.Frame(model_voice_section)
        voice_copy_actions.grid(row=8, column=0, sticky="ew", pady=(12, 0))
        for index, (label, command) in enumerate(
            [
                ("voice 결과 복사", self.copy_voice_result),
                ("브리핑 복사", self.copy_voice_briefing),
                ("voice timeline 복사", self.copy_voice_timeline),
            ]
        ):
            ttk.Button(voice_copy_actions, text=label, command=command).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, 8 if index < 2 else 0),
            )
            voice_copy_actions.columnconfigure(index, weight=1)

        visual_section.columnconfigure(0, weight=1)
        visual_section.rowconfigure(3, weight=1)

        visual_intro = ttk.LabelFrame(visual_section, text="Visual Supervisor 안내", padding=12)
        visual_intro.grid(row=0, column=0, sticky="ew")
        visual_intro.columnconfigure(0, weight=1)
        ttk.Label(
            visual_intro,
            text=(
                "Phase 5에서는 Codex 네이티브 결과와 현재 판단만으로 부족할 때만 시각 증거를 붙입니다. "
                "즉, 무조건 OCR을 돌리는 것이 아니라 필요한 화면만 골라 contradiction를 확인하는 감독층입니다."
            ),
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        visual_settings = ttk.LabelFrame(visual_section, text="시각 감독 설정", padding=12)
        visual_settings.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        visual_settings.columnconfigure(1, weight=1)
        visual_settings.columnconfigure(3, weight=1)

        self.visual_target_mode_var = StringVar()
        self.visual_capture_scope_var = StringVar()
        self.visual_retention_var = StringVar()
        self.visual_sensitive_risk_var = StringVar(value=self.session.visual.sensitive_content_risk)

        for option in VISUAL_TARGET_MODE_OPTIONS:
            self.visual_target_choice_by_label[option.title] = option.mode_id
            self.visual_target_label_by_id[option.mode_id] = option.title
        for option in VISUAL_CAPTURE_SCOPE_OPTIONS:
            self.visual_scope_choice_by_label[option.title] = option.scope_id
            self.visual_scope_label_by_id[option.scope_id] = option.title
        for option in VISUAL_RETENTION_OPTIONS:
            self.visual_retention_choice_by_label[option.title] = option.retention_id
            self.visual_retention_label_by_id[option.retention_id] = option.title

        ttk.Label(visual_settings, text="타깃 모드").grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.visual_target_combo = ttk.Combobox(
            visual_settings,
            textvariable=self.visual_target_mode_var,
            state="readonly",
            values=list(self.visual_target_choice_by_label.keys()),
        )
        self.visual_target_combo.grid(row=0, column=1, sticky="ew")
        self.visual_target_combo.bind("<<ComboboxSelected>>", self._on_visual_settings_changed)

        ttk.Label(visual_settings, text="캡처 범위").grid(row=0, column=2, sticky="w", padx=(16, 12))
        self.visual_scope_combo = ttk.Combobox(
            visual_settings,
            textvariable=self.visual_capture_scope_var,
            state="readonly",
            values=list(self.visual_scope_choice_by_label.keys()),
        )
        self.visual_scope_combo.grid(row=0, column=3, sticky="ew")
        self.visual_scope_combo.bind("<<ComboboxSelected>>", self._on_visual_settings_changed)

        ttk.Label(visual_settings, text="보관 힌트").grid(row=1, column=0, sticky="w", pady=(10, 0), padx=(0, 12))
        self.visual_retention_combo = ttk.Combobox(
            visual_settings,
            textvariable=self.visual_retention_var,
            state="readonly",
            values=list(self.visual_retention_choice_by_label.keys()),
        )
        self.visual_retention_combo.grid(row=1, column=1, sticky="ew", pady=(10, 0))
        self.visual_retention_combo.bind("<<ComboboxSelected>>", self._on_visual_settings_changed)

        ttk.Label(visual_settings, text="민감도 위험").grid(row=1, column=2, sticky="w", pady=(10, 0), padx=(16, 12))
        ttk.Entry(visual_settings, textvariable=self.visual_sensitive_risk_var).grid(row=1, column=3, sticky="ew", pady=(10, 0))

        visual_status = ttk.LabelFrame(visual_section, text="현재 시각 상태", padding=12)
        visual_status.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        visual_status.columnconfigure(0, weight=1)
        self.visual_target_status_var = StringVar(value="시각 캡처 planner 상태가 여기에 표시됩니다.")
        self.visual_summary_status_var = StringVar(value="아직 시각 판단 결과가 없습니다.")
        self.visual_guard_status_var = StringVar(value="capture safety와 retention 기준이 여기에 표시됩니다.")
        ttk.Label(visual_status, textvariable=self.visual_target_status_var, wraplength=760, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(visual_status, textvariable=self.visual_summary_status_var, wraplength=760, justify="left").grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Label(visual_status, textvariable=self.visual_guard_status_var, wraplength=760, justify="left").grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )

        visual_inputs = ttk.LabelFrame(visual_section, text="기대 화면 / 관찰 메모", padding=12)
        visual_inputs.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        visual_inputs.columnconfigure(0, weight=1)
        visual_inputs.columnconfigure(1, weight=1)
        visual_inputs.rowconfigure(1, weight=1)
        visual_inputs.rowconfigure(3, weight=1)
        visual_inputs.rowconfigure(5, weight=1)

        ttk.Label(visual_inputs, text="기대 페이지 / 화면").grid(row=0, column=0, sticky="w")
        self.visual_expected_page = ScrolledText(visual_inputs, height=3, wrap="word")
        self.visual_expected_page.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(4, 8))

        ttk.Label(visual_inputs, text="관찰 포인트").grid(row=0, column=1, sticky="w")
        self.visual_focus = ScrolledText(visual_inputs, height=3, wrap="word")
        self.visual_focus.grid(row=1, column=1, sticky="nsew", pady=(4, 8))

        ttk.Label(visual_inputs, text="기대 신호").grid(row=2, column=0, sticky="w")
        self.visual_expected_signals = ScrolledText(visual_inputs, height=4, wrap="word")
        self.visual_expected_signals.grid(row=3, column=0, sticky="nsew", padx=(0, 8), pady=(4, 8))

        ttk.Label(visual_inputs, text="금지 / mismatch 신호").grid(row=2, column=1, sticky="w")
        self.visual_disallowed_signals = ScrolledText(visual_inputs, height=4, wrap="word")
        self.visual_disallowed_signals.grid(row=3, column=1, sticky="nsew", pady=(4, 8))

        ttk.Label(visual_inputs, text="현재 관찰 메모").grid(row=4, column=0, columnspan=2, sticky="w")
        self.visual_observed_notes = ScrolledText(visual_inputs, height=5, wrap="word")
        self.visual_observed_notes.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(4, 0))

        visual_actions = ttk.Frame(visual_section)
        visual_actions.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        for index, (label, command) in enumerate(
            [
                ("시각 패킷 새로고침", self.refresh_visual_evidence),
                ("시각 재판단", self.run_visual_rejudge_now),
                ("패킷 복사", self.copy_visual_packet),
                ("관찰 프롬프트 복사", self.copy_visual_prompt),
                ("요약 복사", self.copy_visual_summary),
                ("타임라인 복사", self.copy_visual_timeline),
            ]
        ):
            ttk.Button(visual_actions, text=label, command=command).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, 8 if index < 5 else 0),
            )
            visual_actions.columnconfigure(index, weight=1)

        visual_body = ttk.Frame(visual_section)
        visual_body.grid(row=5, column=0, sticky="nsew", pady=(12, 0))
        visual_body.columnconfigure(0, weight=1)
        visual_body.columnconfigure(1, weight=1)
        visual_body.rowconfigure(0, weight=1)
        visual_body.rowconfigure(1, weight=1)

        visual_packet_frame = ttk.LabelFrame(visual_body, text="Visual Evidence Packet", padding=12)
        visual_packet_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        visual_packet_frame.columnconfigure(0, weight=1)
        visual_packet_frame.rowconfigure(1, weight=1)
        self.visual_packet_state_var = StringVar(value="visual evidence packet 초안이 여기에 표시됩니다.")
        ttk.Label(visual_packet_frame, textvariable=self.visual_packet_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.visual_packet_preview = ScrolledText(visual_packet_frame, height=12, wrap="word", state="disabled")
        self.visual_packet_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        visual_prompt_frame = ttk.LabelFrame(visual_body, text="Observation Prompt", padding=12)
        visual_prompt_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        visual_prompt_frame.columnconfigure(0, weight=1)
        visual_prompt_frame.rowconfigure(1, weight=1)
        self.visual_prompt_state_var = StringVar(value="시각 관찰 프롬프트가 여기에 표시됩니다.")
        ttk.Label(visual_prompt_frame, textvariable=self.visual_prompt_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.visual_prompt_preview = ScrolledText(visual_prompt_frame, height=12, wrap="word", state="disabled")
        self.visual_prompt_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        visual_summary_frame = ttk.LabelFrame(visual_body, text="Visual Summary / Contradiction", padding=12)
        visual_summary_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        visual_summary_frame.columnconfigure(0, weight=1)
        visual_summary_frame.rowconfigure(1, weight=1)
        self.visual_summary_state_var = StringVar(value="시각 요약과 contradiction 결과가 여기에 표시됩니다.")
        ttk.Label(visual_summary_frame, textvariable=self.visual_summary_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.visual_summary_preview = ScrolledText(visual_summary_frame, height=12, wrap="word", state="disabled")
        self.visual_summary_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        visual_timeline_frame = ttk.LabelFrame(visual_body, text="Visual Timeline / Safety Guard", padding=12)
        visual_timeline_frame.grid(row=1, column=1, sticky="nsew")
        visual_timeline_frame.columnconfigure(0, weight=1)
        visual_timeline_frame.rowconfigure(1, weight=1)
        self.visual_timeline_state_var = StringVar(value="시각 이력과 capture safety 메모가 여기에 표시됩니다.")
        ttk.Label(visual_timeline_frame, textvariable=self.visual_timeline_state_var, wraplength=360, justify="left").grid(
            row=0, column=0, sticky="w"
        )
        self.visual_timeline_preview = ScrolledText(visual_timeline_frame, height=12, wrap="word", state="disabled")
        self.visual_timeline_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

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
            style="RailNav.TButton",
            command=lambda current=section_id: self._select_control_center_section(current),
        )
        button.pack(fill="x", pady=(0, 8))
        frame = ttk.Frame(self.control_content, padding=6, style="DeckRoot.TFrame")
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
            button.configure(text=label, style="RailNavActive.TButton" if current_id == section_id else "RailNav.TButton")

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

    def _deep_integration_mode_label_for_id(self, mode_id: str) -> str:
        return self.deep_integration_mode_label_by_id.get(
            mode_id,
            next(iter(self.deep_integration_mode_label_by_id.values()), ""),
        )

    def _current_deep_integration_mode_id(self) -> str:
        label = self.deep_integration_mode_var.get().strip()
        return self.deep_integration_mode_choice_by_label.get(
            label,
            next(iter(self.deep_integration_mode_choice_by_label.values()), ""),
        )

    def _deep_integration_readiness_label_for_id(self, readiness_id: str) -> str:
        return self.deep_integration_readiness_label_by_id.get(
            readiness_id,
            next(iter(self.deep_integration_readiness_label_by_id.values()), ""),
        )

    def _current_app_server_readiness_id(self) -> str:
        label = self.deep_app_server_readiness_var.get().strip()
        return self.deep_integration_readiness_choice_by_label.get(
            label,
            next(iter(self.deep_integration_readiness_choice_by_label.values()), ""),
        )

    def _current_cloud_trigger_readiness_id(self) -> str:
        label = self.deep_cloud_trigger_readiness_var.get().strip()
        return self.deep_integration_readiness_choice_by_label.get(
            label,
            next(iter(self.deep_integration_readiness_choice_by_label.values()), ""),
        )

    def _live_ops_profile_label_for_id(self, profile_id: str) -> str:
        return self.live_ops_profile_label_by_id.get(
            profile_id,
            next(iter(self.live_ops_profile_label_by_id.values()), ""),
        )

    def _current_live_ops_profile_id(self) -> str:
        label = self.live_ops_profile_var.get().strip()
        return self.live_ops_profile_choice_by_label.get(
            label,
            next(iter(self.live_ops_profile_choice_by_label.values()), ""),
        )

    def _live_ops_report_label_for_id(self, cadence_id: str) -> str:
        return self.live_ops_report_label_by_id.get(
            cadence_id,
            next(iter(self.live_ops_report_label_by_id.values()), ""),
        )

    def _current_live_ops_report_id(self) -> str:
        label = self.live_ops_report_var.get().strip()
        return self.live_ops_report_choice_by_label.get(
            label,
            next(iter(self.live_ops_report_choice_by_label.values()), ""),
        )

    def _live_ops_reentry_label_for_id(self, reentry_id: str) -> str:
        return self.live_ops_reentry_label_by_id.get(
            reentry_id,
            next(iter(self.live_ops_reentry_label_by_id.values()), ""),
        )

    def _current_live_ops_reentry_id(self) -> str:
        label = self.live_ops_reentry_var.get().strip()
        return self.live_ops_reentry_choice_by_label.get(
            label,
            next(iter(self.live_ops_reentry_choice_by_label.values()), ""),
        )

    def _judgment_mode_label_for_id(self, mode_id: str) -> str:
        return self.judgment_mode_label_by_id.get(
            mode_id,
            next(iter(self.judgment_mode_label_by_id.values()), ""),
        )

    def _current_judgment_engine_mode_id(self) -> str:
        label = self.judgment_engine_mode_var.get().strip()
        return self.judgment_mode_choice_by_label.get(
            label,
            next(iter(self.judgment_mode_choice_by_label.values()), ""),
        )

    def _visual_target_label_for_id(self, mode_id: str) -> str:
        return self.visual_target_label_by_id.get(
            mode_id,
            next(iter(self.visual_target_label_by_id.values()), ""),
        )

    def _current_visual_target_mode_id(self) -> str:
        label = self.visual_target_mode_var.get().strip()
        return self.visual_target_choice_by_label.get(
            label,
            next(iter(self.visual_target_choice_by_label.values()), ""),
        )

    def _visual_scope_label_for_id(self, scope_id: str) -> str:
        return self.visual_scope_label_by_id.get(
            scope_id,
            next(iter(self.visual_scope_label_by_id.values()), ""),
        )

    def _current_visual_scope_id(self) -> str:
        label = self.visual_capture_scope_var.get().strip()
        return self.visual_scope_choice_by_label.get(
            label,
            next(iter(self.visual_scope_choice_by_label.values()), ""),
        )

    def _visual_retention_label_for_id(self, retention_id: str) -> str:
        return self.visual_retention_label_by_id.get(
            retention_id,
            next(iter(self.visual_retention_label_by_id.values()), ""),
        )

    def _current_visual_retention_id(self) -> str:
        label = self.visual_retention_var.get().strip()
        return self.visual_retention_choice_by_label.get(
            label,
            next(iter(self.visual_retention_choice_by_label.values()), ""),
        )

    def _recent_log_lines(self, limit: int = 24) -> list[str]:
        try:
            text = self.log_text.get("1.0", END)
        except TclError:
            return []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines[-limit:]

    def _refresh_judgment_panel(self, session: SessionConfig | None = None) -> None:
        active_session = session
        if active_session is None:
            try:
                active_session = self._collect_session()
            except Exception:
                active_session = self.session

        mode = active_session.judgment.selected_mode()
        mode_label = self._judgment_mode_label_for_id(mode.mode_id)
        if mode_label and self.judgment_engine_mode_var.get() != mode_label:
            self.judgment_engine_mode_var.set(mode_label)
        self.judgment_model_name_var.set(active_session.judgment.model_name)
        self.judgment_confidence_var.set(str(active_session.judgment.confidence_threshold))

        packet_text = self.runtime.last_judgment_packet
        prompt_text = self.runtime.last_judgment_prompt
        response_text = self.runtime.last_judgment_response
        if not packet_text:
            packet_text = self.engine.serialize_judgment_packet(
                self.engine.build_judgment_packet(active_session, self.runtime, self._recent_log_lines())
            )
        if not prompt_text:
            prompt_text = self.engine.build_judgment_prompt(
                active_session,
                self.runtime,
                packet=self.engine.build_judgment_packet(active_session, self.runtime, self._recent_log_lines()),
            )
        timeline_text = self.engine.build_judgment_timeline(self.runtime)
        if not response_text.strip():
            response_text = "아직 검증된 판단 응답이 없습니다. '재판단 실행'으로 현재 상태를 평가해 보세요."

        self._current_judgment_packet = packet_text
        self._current_judgment_prompt = prompt_text
        self._current_judgment_response = response_text
        self._current_judgment_timeline = timeline_text

        self.judgment_engine_status_var.set(
            f"엔진 모드: {mode.title} | 모델 {active_session.judgment.model_name} | threshold {active_session.judgment.confidence_threshold:.2f}"
        )
        if self.runtime.last_judgment.has_result:
            result = self.runtime.last_judgment
            follow_up = ", ".join(result.follow_up_actions[:3]) if result.follow_up_actions else "후속 행동 없음"
            self.judgment_result_status_var.set(
                f"최근 판단: {result.decision} | {result.message_to_user or result.reason}"
            )
            self.judgment_source_status_var.set(
                f"출처 {result.source or '알 수 없음'} | 신뢰도 {result.confidence:.2f} | 위험 {result.risk_level}"
            )
            self.judgment_follow_up_var.set(f"후속 행동: {follow_up}")
            self.judgment_response_state_var.set("검증과 강등 규칙이 반영된 최종 판단 응답입니다.")
        else:
            self.judgment_result_status_var.set("아직 판단 결과가 없습니다. 재판단 실행으로 현재 상태를 점검할 수 있습니다.")
            self.judgment_source_status_var.set("출처 / 신뢰도 / 위험 정보는 판단 후에 표시됩니다.")
            self.judgment_follow_up_var.set("후속 행동 요약은 판단 후에 표시됩니다.")
            self.judgment_response_state_var.set("아직 판단을 실행하지 않았습니다.")

        self.judgment_packet_state_var.set("현재 프로젝트 / 런타임 / 최근 로그를 묶은 judgment input packet입니다.")
        self.judgment_prompt_state_var.set("정책 시스템과 입력 패킷을 조합한 judgment prompt 초안입니다.")
        self.judgment_timeline_state_var.set("최근 판단 이력과 근거 요약, follow-up 메모를 함께 보여줍니다.")

        self._set_readonly_text(self.judgment_packet_preview, packet_text)
        self._set_readonly_text(self.judgment_prompt_preview, prompt_text)
        self._set_readonly_text(self.judgment_response_preview, response_text)
        self._set_readonly_text(self.judgment_timeline_preview, timeline_text)

    def _on_judgment_engine_mode_selected(self, _event=None) -> None:
        self._refresh_judgment_panel()

    def _refresh_visual_panel(self, session: SessionConfig | None = None) -> None:
        active_session = session
        if active_session is None:
            try:
                active_session = self._collect_session()
            except Exception:
                active_session = self.session

        target_label = self._visual_target_label_for_id(active_session.visual.target_mode_id)
        if target_label and self.visual_target_mode_var.get() != target_label:
            self.visual_target_mode_var.set(target_label)
        scope_label = self._visual_scope_label_for_id(active_session.visual.capture_scope_id)
        if scope_label and self.visual_capture_scope_var.get() != scope_label:
            self.visual_capture_scope_var.set(scope_label)
        retention_label = self._visual_retention_label_for_id(active_session.visual.retention_hint_id)
        if retention_label and self.visual_retention_var.get() != retention_label:
            self.visual_retention_var.set(retention_label)
        self.visual_sensitive_risk_var.set(active_session.visual.sensitive_content_risk)

        packet = self.engine.build_visual_evidence_packet(active_session, self.runtime, self._recent_log_lines())
        prompt = self.engine.build_visual_observation_prompt(active_session, self.runtime, packet=packet)
        summary_text = self.runtime.last_visual_summary or "아직 시각 판단 결과가 없습니다. '시각 재판단'으로 현재 화면 근거를 점검해 보세요."
        timeline = self.engine.build_visual_timeline(self.runtime)

        self._current_visual_packet = self.engine.serialize_visual_evidence_packet(packet)
        self._current_visual_prompt = prompt
        self._current_visual_summary = summary_text
        self._current_visual_timeline = timeline

        target_meta = packet.get("target_meta", {})
        safety = packet.get("safety", {})
        self.visual_target_status_var.set(
            f"현재 planner: {target_meta.get('target_label', '화면')} | trigger {target_meta.get('trigger', 'none')} | priority {target_meta.get('priority', 'medium')}"
        )
        if self.runtime.last_visual_result.has_result:
            result = self.runtime.last_visual_result
            self.visual_summary_status_var.set(
                f"최근 시각 판단: contradiction {result.contradiction_level} | hint {result.decision_hint} | {result.message_to_user}"
            )
        else:
            self.visual_summary_status_var.set("아직 시각 판단 결과가 없습니다. 현재 단계와 최근 캡처를 기준으로 planner만 미리 보여줍니다.")
        self.visual_guard_status_var.set(
            f"capture scope {safety.get('capture_scope_label', '미정')} | retention {safety.get('retention_label', '미정')} | sensitive risk {safety.get('sensitive_content_risk', 'medium')}"
        )

        self.visual_packet_state_var.set("무엇을 왜 캡처하고 어떤 신호를 볼지 정리한 visual evidence packet입니다.")
        self.visual_prompt_state_var.set("시각 근거를 판정 중심으로 읽게 하는 observation prompt입니다.")
        self.visual_summary_state_var.set("최근 시각 판단 결과, contradiction, decision hint를 함께 보여줍니다.")
        self.visual_timeline_state_var.set("최근 시각 이력과 capture safety 메모를 함께 보여줍니다.")

        self._set_readonly_text(self.visual_packet_preview, self._current_visual_packet)
        self._set_readonly_text(self.visual_prompt_preview, self._current_visual_prompt)
        self._set_readonly_text(self.visual_summary_preview, summary_text)
        self._set_readonly_text(self.visual_timeline_preview, timeline)

    def _on_visual_settings_changed(self, _event=None) -> None:
        self._refresh_visual_panel()

    def refresh_visual_evidence(self) -> None:
        try:
            self.session = self._collect_session()
            self._refresh_visual_panel(self.session)
            self._save_session_quietly()
            self._log("현재 단계와 최근 로그 기준으로 visual evidence packet과 observation prompt를 다시 만들었습니다.")
        except Exception as exc:
            messagebox.showerror("시각 패킷 새로고침 실패", str(exc))

    def run_visual_rejudge_now(self) -> None:
        try:
            self.session = self._collect_session()
            visual_result, judgment_result = self.engine.run_visual_rejudge(
                self.session,
                self.runtime,
                recent_log_lines=self._recent_log_lines(),
            )
            if judgment_result.decision == "retry" and (judgment_result.next_prompt_to_codex or "").strip():
                self.runtime.update_prompt_draft(judgment_result.next_prompt_to_codex.strip())
            if judgment_result.decision in {"pause", "ask_user"}:
                self.runtime.set_operator_pause(judgment_result.message_to_user or judgment_result.reason)
            elif judgment_result.decision == "continue":
                self.runtime.clear_operator_pause()
            self._save_session_quietly()
            self._refresh_prompt_panel_from_current_session()
            self._refresh_runtime_labels()
            self._refresh_visual_panel(self.session)
            self._log(
                f"시각 재판단 완료: contradiction {visual_result.contradiction_level} -> {judgment_result.decision}"
            )
        except Exception as exc:
            messagebox.showerror("시각 재판단 실패", str(exc))

    def copy_visual_packet(self) -> None:
        try:
            if not self._current_visual_packet.strip():
                self._refresh_visual_panel()
            self._copy_text_to_clipboard(
                title="Visual Packet 복사",
                text=self._current_visual_packet,
                success_log="Visual evidence packet을 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Visual packet 복사 실패", str(exc))

    def copy_visual_prompt(self) -> None:
        try:
            if not self._current_visual_prompt.strip():
                self._refresh_visual_panel()
            self._copy_text_to_clipboard(
                title="Visual Prompt 복사",
                text=self._current_visual_prompt,
                success_log="Observation prompt를 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Observation prompt 복사 실패", str(exc))

    def copy_visual_summary(self) -> None:
        try:
            if not self._current_visual_summary.strip():
                self._refresh_visual_panel()
            self._copy_text_to_clipboard(
                title="Visual Summary 복사",
                text=self._current_visual_summary,
                success_log="시각 요약과 contradiction 결과를 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Visual summary 복사 실패", str(exc))

    def copy_visual_timeline(self) -> None:
        try:
            if not self._current_visual_timeline.strip():
                self._refresh_visual_panel()
            self._copy_text_to_clipboard(
                title="Visual Timeline 복사",
                text=self._current_visual_timeline,
                success_log="시각 타임라인과 safety 메모를 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Visual timeline 복사 실패", str(exc))

    def run_judgment_now(self) -> None:
        try:
            self.session = self._collect_session()
            result = self.engine.run_judgment(
                self.session,
                self.runtime,
                recent_log_lines=self._recent_log_lines(),
            )
            if result.decision == "retry" and (result.next_prompt_to_codex or "").strip():
                self.runtime.update_prompt_draft(result.next_prompt_to_codex.strip())
            if result.decision in {"pause", "ask_user"}:
                self.runtime.set_operator_pause(result.message_to_user or result.reason)
            elif result.decision == "continue":
                self.runtime.clear_operator_pause()
            self._save_session_quietly()
            self._refresh_prompt_panel_from_current_session()
            self._refresh_runtime_labels()
            self._log(
                f"재판단 완료: {result.decision} | conf {result.confidence:.2f} | risk {result.risk_level}"
            )
            for note in result.validation_notes:
                self._log(f"[판단 검증] {note}")
        except Exception as exc:
            messagebox.showerror("재판단 실패", str(exc))

    def retry_now(self) -> None:
        result = self.runtime.last_judgment
        if not result.has_result or result.decision != "retry" or not (result.next_prompt_to_codex or "").strip():
            messagebox.showerror("재지시 실패", "현재 retry 판단 결과가 없어 보정 프롬프트를 바로 보낼 수 없습니다.")
            return
        self.runtime.update_prompt_draft(result.next_prompt_to_codex.strip())
        self._refresh_prompt_panel_from_current_session()
        self._log("판단 결과의 보정 프롬프트를 현재 단계 편집본으로 반영했습니다.")
        self.send_next_step()

    def copy_judgment_packet(self) -> None:
        try:
            if not self._current_judgment_packet.strip():
                self._refresh_judgment_panel()
            self._copy_text_to_clipboard(
                title="Judgment Packet 복사",
                text=self._current_judgment_packet,
                success_log="Judgment packet을 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("패킷 복사 실패", str(exc))

    def copy_judgment_prompt(self) -> None:
        try:
            if not self._current_judgment_prompt.strip():
                self._refresh_judgment_panel()
            self._copy_text_to_clipboard(
                title="Judgment Prompt 복사",
                text=self._current_judgment_prompt,
                success_log="Judgment prompt를 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("프롬프트 복사 실패", str(exc))

    def copy_judgment_response(self) -> None:
        try:
            if not self._current_judgment_response.strip():
                self._refresh_judgment_panel()
            self._copy_text_to_clipboard(
                title="Judgment Response 복사",
                text=self._current_judgment_response,
                success_log="검증된 판단 응답을 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("응답 복사 실패", str(exc))

    def copy_judgment_timeline(self) -> None:
        try:
            if not self._current_judgment_timeline.strip():
                self._refresh_judgment_panel()
            self._copy_text_to_clipboard(
                title="Judgment Timeline 복사",
                text=self._current_judgment_timeline,
                success_log="판단 타임라인과 근거 요약을 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("타임라인 복사 실패", str(exc))

    def _refresh_visual_panel(self, session: SessionConfig | None = None) -> None:
        active_session = session
        if active_session is None:
            try:
                active_session = self._collect_session()
            except Exception:
                active_session = self.session

        target_label = self._visual_target_label_for_id(active_session.visual.target_mode_id)
        if target_label and self.visual_target_mode_var.get() != target_label:
            self.visual_target_mode_var.set(target_label)
        scope_label = self._visual_scope_label_for_id(active_session.visual.capture_scope_id)
        if scope_label and self.visual_capture_scope_var.get() != scope_label:
            self.visual_capture_scope_var.set(scope_label)
        retention_label = self._visual_retention_label_for_id(active_session.visual.retention_hint_id)
        if retention_label and self.visual_retention_var.get() != retention_label:
            self.visual_retention_var.set(retention_label)
        self.visual_sensitive_risk_var.set(active_session.visual.sensitive_content_risk)

        packet = self.engine.build_visual_evidence_packet(active_session, self.runtime, self._recent_log_lines())
        prompt = self.engine.build_visual_observation_prompt(active_session, self.runtime, packet=packet)
        summary_text = self.runtime.last_visual_summary or "아직 시각 판단 결과가 없습니다. '시각 재판단'으로 현재 화면 근거를 점검해 보세요."
        timeline = self.engine.build_visual_timeline(self.runtime)

        self._current_visual_packet = self.engine.serialize_visual_evidence_packet(packet)
        self._current_visual_prompt = prompt
        self._current_visual_summary = summary_text
        self._current_visual_timeline = timeline

        target_meta = packet.get("target_meta", {})
        safety = packet.get("safety", {})
        self.visual_target_status_var.set(
            f"현재 planner: {target_meta.get('target_label', '화면')} | trigger {target_meta.get('trigger', 'none')} | priority {target_meta.get('priority', 'medium')}"
        )
        if self.runtime.last_visual_result.has_result:
            result = self.runtime.last_visual_result
            self.visual_summary_status_var.set(
                f"최근 시각 판단: contradiction {result.contradiction_level} | hint {result.decision_hint} | {result.message_to_user}"
            )
        else:
            self.visual_summary_status_var.set("아직 시각 판단 결과가 없습니다. 현재 단계와 최근 캡처를 기준으로 planner만 미리 보여줍니다.")
        self.visual_guard_status_var.set(
            f"capture scope {safety.get('capture_scope_label', '미정')} | retention {safety.get('retention_label', '미정')} | sensitive risk {safety.get('sensitive_content_risk', 'medium')}"
        )

        self.visual_packet_state_var.set("무엇을 왜 캡처하고 어떤 신호를 볼지 정리한 visual evidence packet입니다.")
        self.visual_prompt_state_var.set("시각 근거를 판정 중심으로 읽게 하는 observation prompt입니다.")
        self.visual_summary_state_var.set("최근 시각 판단 결과, contradiction, decision hint를 함께 보여줍니다.")
        self.visual_timeline_state_var.set("최근 시각 이력과 capture safety 메모를 함께 보여줍니다.")

        self._set_readonly_text(self.visual_packet_preview, self._current_visual_packet)
        self._set_readonly_text(self.visual_prompt_preview, self._current_visual_prompt)
        self._set_readonly_text(self.visual_summary_preview, summary_text)
        self._set_readonly_text(self.visual_timeline_preview, timeline)

    def _on_visual_settings_changed(self, _event=None) -> None:
        self._refresh_visual_panel()

    def refresh_visual_evidence(self) -> None:
        try:
            self.session = self._collect_session()
            self._refresh_visual_panel(self.session)
            self._save_session_quietly()
            self._log("현재 단계와 최근 로그 기준으로 visual evidence packet과 observation prompt를 다시 만들었습니다.")
        except Exception as exc:
            messagebox.showerror("시각 패킷 새로고침 실패", str(exc))

    def run_visual_rejudge_now(self) -> None:
        try:
            self.session = self._collect_session()
            visual_result, judgment_result = self.engine.run_visual_rejudge(
                self.session,
                self.runtime,
                recent_log_lines=self._recent_log_lines(),
            )
            if judgment_result.decision == "retry" and (judgment_result.next_prompt_to_codex or "").strip():
                self.runtime.update_prompt_draft(judgment_result.next_prompt_to_codex.strip())
            if judgment_result.decision in {"pause", "ask_user"}:
                self.runtime.set_operator_pause(judgment_result.message_to_user or judgment_result.reason)
            elif judgment_result.decision == "continue":
                self.runtime.clear_operator_pause()
            self._save_session_quietly()
            self._refresh_prompt_panel_from_current_session()
            self._refresh_runtime_labels()
            self._refresh_visual_panel(self.session)
            self._log(
                f"시각 재판단 완료: contradiction {visual_result.contradiction_level} -> {judgment_result.decision}"
            )
        except Exception as exc:
            messagebox.showerror("시각 재판단 실패", str(exc))

    def copy_visual_packet(self) -> None:
        try:
            if not self._current_visual_packet.strip():
                self._refresh_visual_panel()
            self._copy_text_to_clipboard(
                title="Visual Packet 복사",
                text=self._current_visual_packet,
                success_log="Visual evidence packet을 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Visual packet 복사 실패", str(exc))

    def copy_visual_prompt(self) -> None:
        try:
            if not self._current_visual_prompt.strip():
                self._refresh_visual_panel()
            self._copy_text_to_clipboard(
                title="Visual Prompt 복사",
                text=self._current_visual_prompt,
                success_log="Observation prompt를 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Observation prompt 복사 실패", str(exc))

    def copy_visual_summary(self) -> None:
        try:
            if not self._current_visual_summary.strip():
                self._refresh_visual_panel()
            self._copy_text_to_clipboard(
                title="Visual Summary 복사",
                text=self._current_visual_summary,
                success_log="시각 요약과 contradiction 결과를 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Visual summary 복사 실패", str(exc))

    def copy_visual_timeline(self) -> None:
        try:
            if not self._current_visual_timeline.strip():
                self._refresh_visual_panel()
            self._copy_text_to_clipboard(
                title="Visual Timeline 복사",
                text=self._current_visual_timeline,
                success_log="시각 타임라인과 safety 메모를 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Visual timeline 복사 실패", str(exc))

    def _refresh_voice_panel(self, session: SessionConfig | None = None) -> None:
        active_session = session
        if active_session is None:
            try:
                active_session = self._collect_session()
            except Exception:
                active_session = self.session

        self.voice_language_var.set(active_session.voice.language_code)
        self.voice_microphone_var.set(active_session.voice.microphone_name)
        self.voice_speaker_var.set(active_session.voice.speaker_name)
        self.voice_auto_brief_var.set(active_session.voice.auto_brief_enabled)
        self.voice_confirmation_var.set(active_session.voice.confirmation_enabled)
        self.voice_spoken_feedback_var.set(active_session.voice.spoken_feedback_enabled)
        self.voice_ambient_ready_var.set(active_session.voice.ambient_ready_enabled)

        transcript_text = self.runtime.voice_last_transcript.strip()
        current_transcript = self.voice_transcript_input.get("1.0", END).rstrip("\n")
        if transcript_text and current_transcript != transcript_text:
            self._set_scrolled_text(self.voice_transcript_input, transcript_text)

        if self.runtime.last_voice_result.has_result:
            result = self.runtime.last_voice_result
            result_text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
            self.voice_result_status_var.set(
                f"최근 의도: {result.normalized_intent_id or '알 수 없음'} | 동작 {result.action_status or '없음'} | 신뢰도 {result.intent_confidence:.2f}"
            )
            self.voice_capture_status_var.set(
                f"음성 캡처: {self.runtime.voice_capture_state} | 마지막 전사 길이 {len(result.transcript_text.strip())}자"
            )
            self.voice_result_state_var.set("최근 voice intent 결과와 action routing 상태입니다.")
        else:
            result_text = "아직 voice intent 결과가 없습니다."
            self.voice_capture_status_var.set(
                f"voice capture: {self.runtime.voice_capture_state} | transcript를 넣고 'voice 실행'을 눌러주세요."
            )
            self.voice_result_status_var.set("아직 voice intent 결과가 없습니다.")
            self.voice_result_state_var.set("voice intent 결과가 여기 표시됩니다.")

        if self.runtime.voice_pending_action_id:
            self.voice_confirmation_status_var.set(
                "대기 중 확인: "
                f"{self.runtime.voice_pending_action_id} | {self.runtime.voice_pending_confirmation_text or '확인이 필요합니다.'}"
            )
        else:
            self.voice_confirmation_status_var.set("대기 중인 voice confirmation이 없습니다.")

        briefing_text = self.runtime.voice_last_briefing.strip()
        if not briefing_text:
            briefing_text = self.engine.build_voice_briefing(active_session, self.runtime, intent_id="status_summary")
        self.voice_briefing_state_var.set(
            "spoken feedback는 현재 텍스트 브리핑으로 검증합니다."
            if active_session.voice.spoken_feedback_enabled
            else "spoken feedback는 꺼져 있지만 브리핑 초안은 계속 생성합니다."
        )

        timeline_text = self.engine.build_voice_timeline(self.runtime)
        self.voice_timeline_state_var.set("최근 voice history, confirmation guard, pending action을 함께 보여줍니다.")

        self._current_voice_result = result_text
        self._current_voice_briefing = briefing_text
        self._current_voice_timeline = timeline_text
        self._set_readonly_text(self.voice_result_preview, result_text)
        self._set_readonly_text(self.voice_briefing_preview, briefing_text)
        self._set_readonly_text(self.voice_timeline_preview, timeline_text)

    def _dispatch_voice_action(self, action_id: str) -> None:
        if action_id == "open_settings":
            self.open_control_center()
            self._select_control_center_section("model_voice")
            return
        self.perform_surface_action(action_id)

    def toggle_voice_capture(self) -> None:
        try:
            if self.runtime.voice_capture_state == "recording":
                self.runtime.voice_capture_state = "idle"
                self._log("push-to-talk 대기 상태로 돌아왔습니다.")
            else:
                self.runtime.voice_capture_state = "recording"
                self._log("push-to-talk 준비 상태입니다. transcript를 붙여넣거나 직접 적은 뒤 'voice 실행'을 눌러주세요.")
            self._save_session_quietly()
            self._refresh_runtime_labels()
            self._refresh_voice_panel(self.session)
        except Exception as exc:
            messagebox.showerror("Push-to-Talk 전환 실패", str(exc))

    def run_voice_command_now(self) -> None:
        try:
            self.session = self._collect_session()
            transcript = self.voice_transcript_input.get("1.0", END).strip()
            self.runtime.voice_last_transcript = transcript
            result = self.engine.run_voice_command(self.session, self.runtime, transcript)

            if result.spoken_briefing_text.strip():
                self.runtime.voice_last_briefing = result.spoken_briefing_text.strip()

            if result.action_status == "executed" and result.action_id:
                self._dispatch_voice_action(result.action_id)

            self._save_session_quietly()
            self._refresh_prompt_panel_from_current_session()
            self._refresh_runtime_labels()
            self._refresh_voice_panel(self.session)

            self._log(
                "voice intent 처리: "
                f"{result.normalized_intent_id or '알 수 없음'} -> {result.action_status or '없음'}"
            )
            if result.clarification_question:
                self._log(f"[voice clarify] {result.clarification_question}")
            if result.action_status == "confirmation_required":
                self._log(
                    "[voice 확인 필요] "
                    f"{result.action_id or 'action'} | {result.message_to_user or '한 번 더 확인이 필요합니다.'}"
                )
            if self.session.voice.spoken_feedback_enabled and result.spoken_briefing_text.strip():
                self._log(f"[voice 브리핑] {result.spoken_briefing_text.strip()}")
        except Exception as exc:
            messagebox.showerror("Voice 실행 실패", str(exc))

    def play_voice_briefing_now(self) -> None:
        try:
            self.session = self._collect_session()
            briefing = self.engine.build_voice_briefing(self.session, self.runtime, intent_id="status_summary")
            self.runtime.voice_last_briefing = briefing
            self._save_session_quietly()
            self._refresh_voice_panel(self.session)
            self._refresh_runtime_labels()
            if self.session.voice.spoken_feedback_enabled and briefing.strip():
                self._log(f"[voice 브리핑] {briefing.strip()}")
            else:
                self._log("현재 상태 브리핑 초안을 새로 만들었습니다.")
        except Exception as exc:
            messagebox.showerror("브리핑 생성 실패", str(exc))

    def confirm_pending_voice_action(self) -> None:
        if not self.runtime.voice_pending_action_id:
            messagebox.showerror("Voice 확인", "현재 대기 중인 voice confirmation이 없습니다.")
            return
        try:
            self.session = self._collect_session()
            result = self.engine.run_voice_command(self.session, self.runtime, "확인")
            if result.spoken_briefing_text.strip():
                self.runtime.voice_last_briefing = result.spoken_briefing_text.strip()
            if result.action_status == "executed" and result.action_id:
                self._dispatch_voice_action(result.action_id)
            self._save_session_quietly()
            self._refresh_prompt_panel_from_current_session()
            self._refresh_runtime_labels()
            self._refresh_voice_panel(self.session)
            self._log(f"voice 확인 처리: {result.message_to_user or result.normalized_intent_id}")
            if self.session.voice.spoken_feedback_enabled and result.spoken_briefing_text.strip():
                self._log(f"[voice 브리핑] {result.spoken_briefing_text.strip()}")
        except Exception as exc:
            messagebox.showerror("Voice 확인 실패", str(exc))

    def cancel_pending_voice_action(self) -> None:
        if not self.runtime.voice_pending_action_id:
            messagebox.showerror("Voice 취소", "현재 취소할 voice confirmation이 없습니다.")
            return
        try:
            self.session = self._collect_session()
            result = self.engine.run_voice_command(self.session, self.runtime, "취소")
            if result.spoken_briefing_text.strip():
                self.runtime.voice_last_briefing = result.spoken_briefing_text.strip()
            self._save_session_quietly()
            self._refresh_prompt_panel_from_current_session()
            self._refresh_runtime_labels()
            self._refresh_voice_panel(self.session)
            self._log(f"voice 확인 취소: {result.message_to_user or result.normalized_intent_id}")
            if self.session.voice.spoken_feedback_enabled and result.spoken_briefing_text.strip():
                self._log(f"[voice 브리핑] {result.spoken_briefing_text.strip()}")
        except Exception as exc:
            messagebox.showerror("Voice 취소 실패", str(exc))

    def copy_voice_result(self) -> None:
        try:
            if not self._current_voice_result.strip():
                self._refresh_voice_panel()
            self._copy_text_to_clipboard(
                title="Voice Result 복사",
                text=self._current_voice_result,
                success_log="Voice intent 결과를 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Voice result 복사 실패", str(exc))

    def copy_voice_briefing(self) -> None:
        try:
            if not self._current_voice_briefing.strip():
                self._refresh_voice_panel()
            self._copy_text_to_clipboard(
                title="Voice Briefing 복사",
                text=self._current_voice_briefing,
                success_log="현재 voice briefing 초안을 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Voice briefing 복사 실패", str(exc))

    def copy_voice_timeline(self) -> None:
        try:
            if not self._current_voice_timeline.strip():
                self._refresh_voice_panel()
            self._copy_text_to_clipboard(
                title="Voice Timeline 복사",
                text=self._current_voice_timeline,
                success_log="Voice timeline과 guard 상태를 클립보드에 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Voice timeline 복사 실패", str(exc))

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
        self.codex_strategy_mode_var.set(f"추천 방식: {recommended_option.title} | 실제 실행: {effective_option.title}")
        self.codex_strategy_cadence_var.set(f"실행 리듬: {decision.cadence_hint}")
        self.codex_strategy_worktree_var.set(f"워크트리: {decision.worktree_hint}")
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
        self._refresh_deep_integration_panel(active_session)
        self._refresh_live_ops_panel(active_session)

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

    def _refresh_deep_integration_panel(self, session: SessionConfig | None = None) -> None:
        active_session = session
        if active_session is None:
            try:
                active_session = self._collect_session()
            except Exception:
                active_session = self.session

        mode_label = self._deep_integration_mode_label_for_id(active_session.deep_integration.selected_mode_id)
        if mode_label and self.deep_integration_mode_var.get() != mode_label:
            self.deep_integration_mode_var.set(mode_label)
        app_server_label = self._deep_integration_readiness_label_for_id(
            active_session.deep_integration.app_server_readiness_id
        )
        if app_server_label and self.deep_app_server_readiness_var.get() != app_server_label:
            self.deep_app_server_readiness_var.set(app_server_label)
        cloud_label = self._deep_integration_readiness_label_for_id(
            active_session.deep_integration.cloud_trigger_readiness_id
        )
        if cloud_label and self.deep_cloud_trigger_readiness_var.get() != cloud_label:
            self.deep_cloud_trigger_readiness_var.set(cloud_label)
        self.deep_fallback_allowed_var.set(active_session.deep_integration.desktop_fallback_allowed)
        if self.deep_app_server_notes_var.get() != active_session.deep_integration.app_server_notes:
            self.deep_app_server_notes_var.set(active_session.deep_integration.app_server_notes)
        if self.deep_cloud_trigger_notes_var.get() != active_session.deep_integration.cloud_trigger_notes:
            self.deep_cloud_trigger_notes_var.set(active_session.deep_integration.cloud_trigger_notes)

        decision = self.engine.recommend_deep_integration_mode(active_session, self.runtime)
        recommended_option = get_deep_integration_mode_option(decision.recommended_mode_id)
        selected_option = active_session.deep_integration.selected_mode()
        effective_option = get_deep_integration_mode_option(decision.effective_mode_id)

        registry = self.engine.build_deep_integration_capability_registry(active_session, self.runtime)
        handoff = self.engine.build_cross_surface_handoff_bundle(active_session, self.runtime)
        observability = self.engine.build_integration_observability_report(active_session, self.runtime)

        self._current_deep_integration_registry = registry
        self._current_deep_integration_handoff = handoff
        self._current_deep_integration_observability = observability

        self.deep_integration_mode_status_var.set(
            f"추천 방식: {recommended_option.title} | 현재 선택: {selected_option.title} | 실제 적용: {effective_option.title}"
        )
        self.deep_integration_supervisor_var.set(
            f"감독 상태: {decision.supervisor_state} | {decision.supervisor_reason}"
        )
        self.deep_integration_fallback_var.set(
            f"예외 경로: {decision.fallback_state} | {decision.fallback_reason}"
        )
        self.deep_integration_reentry_var.set(
            f"handoff: {decision.handoff_target} | 재진입: {decision.reentry_source} | 다음 검토: {decision.next_review_point}"
        )

        self.deep_integration_registry_state_var.set(
            "현재 Codex native / App Server / cloud trigger readiness를 capability registry로 정리해 보여줍니다."
        )
        self.deep_integration_observability_state_var.set(
            "추천 mode, supervisor state, fallback boundary를 observability 리포트로 보여줍니다."
        )
        self.deep_integration_handoff_state_var.set(
            "현재 프로젝트를 다음 surface로 넘길 때 필요한 handoff bundle을 보여줍니다."
        )

        self._set_readonly_text(self.deep_integration_registry_preview, registry)
        self._set_readonly_text(self.deep_integration_observability_preview, observability)
        self._set_readonly_text(self.deep_integration_handoff_preview, handoff)

    def _on_deep_integration_settings_changed(self, _event=None) -> None:
        preview_session = self._collect_session()
        self._refresh_deep_integration_panel(preview_session)
        self._refresh_project_home(preview_session)

    def refresh_deep_integration_panel_now(self) -> None:
        try:
            self.session = self._collect_session()
            self._refresh_deep_integration_panel(self.session)
            self._refresh_project_home(self.session)
            self._save_session_quietly()
            self._log("Deep Integration 패널을 현재 설정 기준으로 새로고침했습니다.")
        except Exception as exc:
            messagebox.showerror("Deep Integration 새로고침 실패", str(exc))

    def copy_deep_integration_registry(self) -> None:
        try:
            if not self._current_deep_integration_registry.strip():
                self._refresh_deep_integration_panel()
            self._copy_text_to_clipboard(
                title="Capability Registry 복사",
                text=self._current_deep_integration_registry,
                success_log="Deep Integration capability registry를 클립보드로 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Capability registry 복사 실패", str(exc))

    def copy_deep_integration_handoff(self) -> None:
        try:
            if not self._current_deep_integration_handoff.strip():
                self._refresh_deep_integration_panel()
            self._copy_text_to_clipboard(
                title="Handoff Bundle 복사",
                text=self._current_deep_integration_handoff,
                success_log="Deep Integration handoff bundle을 클립보드로 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Handoff bundle 복사 실패", str(exc))

    def copy_deep_integration_observability(self) -> None:
        try:
            if not self._current_deep_integration_observability.strip():
                self._refresh_deep_integration_panel()
            self._copy_text_to_clipboard(
                title="Observability 복사",
                text=self._current_deep_integration_observability,
                success_log="Deep Integration observability 리포트를 클립보드로 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("Observability 복사 실패", str(exc))

    def _refresh_live_ops_panel(self, session: SessionConfig | None = None) -> None:
        active_session = session
        if active_session is None:
            try:
                active_session = self._collect_session()
            except Exception:
                active_session = self.session

        profile_label = self._live_ops_profile_label_for_id(active_session.live_ops.selected_profile_id)
        if profile_label and self.live_ops_profile_var.get() != profile_label:
            self.live_ops_profile_var.set(profile_label)
        report_label = self._live_ops_report_label_for_id(active_session.live_ops.report_cadence_id)
        if report_label and self.live_ops_report_var.get() != report_label:
            self.live_ops_report_var.set(report_label)
        reentry_label = self._live_ops_reentry_label_for_id(active_session.live_ops.reentry_mode_id)
        if reentry_label and self.live_ops_reentry_var.get() != reentry_label:
            self.live_ops_reentry_var.set(reentry_label)
        if self.live_ops_max_steps_var.get() != str(active_session.live_ops.max_unattended_steps):
            self.live_ops_max_steps_var.set(str(active_session.live_ops.max_unattended_steps))

        decision = self.engine.recommend_live_ops_status(active_session, self.runtime)
        profile = active_session.live_ops.selected_profile()
        charter = self.engine.build_live_ops_charter(active_session, self.runtime)
        launchpad = self.engine.build_live_ops_launchpad(active_session, self.runtime)
        reentry_brief = self.engine.build_live_ops_reentry_brief(active_session, self.runtime)
        recovery = self.engine.build_live_ops_recovery_playbook(active_session, self.runtime)
        shift_brief = self.engine.build_live_ops_shift_brief(active_session, self.runtime)

        self._current_live_ops_charter = charter
        self._current_live_ops_launchpad = launchpad
        self._current_live_ops_reentry_brief = reentry_brief
        self._current_live_ops_recovery = recovery
        self._current_live_ops_shift_brief = shift_brief

        self.live_ops_profile_status_var.set(
            f"프로필: {profile.title} | 보고: {active_session.live_ops.selected_report_cadence().title} | 재진입: {active_session.live_ops.selected_reentry_mode().title}"
        )
        self.live_ops_lane_status_var.set(f"운영 레인: {decision.lane_id} | {decision.lane_reason}")
        self.live_ops_touchpoint_var.set(f"터치포인트: {decision.operator_touchpoint} | {decision.reentry_action}")
        self.live_ops_recovery_status_var.set(
            f"복구 단계: {decision.recovery_level} | {decision.recovery_reason}"
        )

        self.live_ops_charter_state_var.set("Codex 실행 전에 운영 원칙과 감독 가드를 정리한 차터입니다.")
        self.live_ops_launchpad_state_var.set("지금 바로 실행할 때 확인할 체크리스트와 즉시 행동을 보여줍니다.")
        self.live_ops_reentry_state_var.set("트리아지와 현재 스레드 결과를 다시 읽고 재진입할 때의 기준을 보여줍니다.")
        self.live_ops_recovery_state_var.set("막힘, 수동 검토, 재시도 상황에서 어떤 수준으로 복구할지 안내합니다.")
        self.live_ops_shift_state_var.set("현재 운영 상태를 운영자 브리프처럼 짧게 요약해 보여줍니다.")

        self._set_readonly_text(self.live_ops_charter_preview, charter)
        self._set_readonly_text(self.live_ops_launchpad_preview, launchpad)
        self._set_readonly_text(self.live_ops_reentry_preview, reentry_brief)
        self._set_readonly_text(self.live_ops_recovery_preview, recovery)
        self._set_readonly_text(self.live_ops_shift_preview, shift_brief)

    def _on_live_ops_settings_changed(self, _event=None) -> None:
        preview_session = self._collect_session()
        self._refresh_live_ops_panel(preview_session)
        self._refresh_project_home(preview_session)

    def refresh_live_ops_panel_now(self) -> None:
        try:
            self.session = self._collect_session()
            self._refresh_live_ops_panel(self.session)
            self._refresh_project_home(self.session)
            self._save_session_quietly()
            self._log("라이브 오퍼레이션 패널을 현재 설정 기준으로 새로고침했습니다.")
        except Exception as exc:
            messagebox.showerror("라이브 오퍼레이션 새로고침 실패", str(exc))

    def copy_live_ops_charter(self) -> None:
        try:
            if not self._current_live_ops_charter.strip():
                self._refresh_live_ops_panel()
            self._copy_text_to_clipboard(
                title="운영 차터 복사",
                text=self._current_live_ops_charter,
                success_log="운영 차터를 클립보드로 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("운영 차터 복사 실패", str(exc))

    def copy_live_ops_reentry_brief(self) -> None:
        try:
            if not self._current_live_ops_reentry_brief.strip():
                self._refresh_live_ops_panel()
            self._copy_text_to_clipboard(
                title="재진입 브리프 복사",
                text=self._current_live_ops_reentry_brief,
                success_log="재진입 브리프를 클립보드로 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("재진입 브리프 복사 실패", str(exc))

    def copy_live_ops_recovery(self) -> None:
        try:
            if not self._current_live_ops_recovery.strip():
                self._refresh_live_ops_panel()
            self._copy_text_to_clipboard(
                title="복구 플레이북 복사",
                text=self._current_live_ops_recovery,
                success_log="복구 플레이북을 클립보드로 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("복구 플레이북 복사 실패", str(exc))

    def copy_live_ops_shift_brief(self) -> None:
        try:
            if not self._current_live_ops_shift_brief.strip():
                self._refresh_live_ops_panel()
            self._copy_text_to_clipboard(
                title="시프트 브리프 복사",
                text=self._current_live_ops_shift_brief,
                success_log="시프트 브리프를 클립보드로 복사했습니다.",
            )
        except Exception as exc:
            messagebox.showerror("시프트 브리프 복사 실패", str(exc))

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
        two_row = popup_width < 470
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
        text_wrap = popup_width - 76
        project_wrap = popup_width - 168

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
            center_width = 1320
        if center_height <= 1:
            center_height = 960
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
            "retry_now": self.retry_now,
            "resume_ready": self.resume_after_pause,
            "start_auto": self.toggle_auto,
            "pause_auto": self.pause_automation,
            "show_summary": self.show_status_summary,
            "open_settings": self.open_control_center,
            "refresh_windows": self.refresh_windows,
            "focus_codex": self.focus_codex,
            "capture_now": self.capture_now,
            "voice_brief": self.play_voice_briefing_now,
            "rejudge": self.run_judgment_now,
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

    def _close_application(self) -> None:
        self.stop_event.set()
        self.runtime.auto_running = False
        try:
            self.control_center.destroy()
        except TclError:
            pass
        self.root.destroy()

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

        if self.runtime.last_judgment.has_result:
            result = self.runtime.last_judgment
            lines.extend(
                [
                    f"판단: {result.decision}",
                    f"판단 근거: {result.reason}",
                    f"신뢰도: {result.confidence:.2f}",
                    f"판단 출처: {result.source or '알 수 없음'}",
                ]
            )

        if self.runtime.last_visual_result.has_result:
            visual_result = self.runtime.last_visual_result
            lines.extend(
                [
                    f"시각 contradiction: {visual_result.contradiction_level}",
                    f"시각 hint: {visual_result.decision_hint}",
                    f"시각 근거: {visual_result.contradiction_reason}",
                    f"시각 관찰: {visual_result.observed_summary}",
                ]
            )

        messagebox.showinfo("javis 요약", "\n\n".join(lines))

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

    def _refresh_project_home(self, session: SessionConfig | None = None) -> None:
        active_session = session or self.session
        steps = active_session.project.steps()
        total_steps = len(steps)
        project_title = active_session.project.project_summary or active_session.project.target_outcome or "프로젝트 정보 미입력"
        target_text = active_session.project.target_outcome or "목표 수준이 아직 없습니다."
        current_strategy = active_session.codex_strategy.selected_preset()
        current_decision = self.engine.recommend_codex_automation_mode(active_session, self.runtime)
        current_mode = get_codex_automation_mode_option(current_decision.effective_mode_id)
        current_deep_decision = self.engine.recommend_deep_integration_mode(active_session, self.runtime)
        current_deep_mode = get_deep_integration_mode_option(current_deep_decision.effective_mode_id)
        current_live_ops = self.engine.recommend_live_ops_status(active_session, self.runtime)
        strategy_text = (
            f"운영 프로필: {current_strategy.title} | 선택 mode: {active_session.codex_strategy.selected_mode().title} | "
            f"실제 launch: {current_mode.title}"
        )
        strategy_text += (
            f"\nDeep integration: {current_deep_mode.title} | supervisor: {current_deep_decision.supervisor_state}"
        )
        strategy_text += f"\n라이브 운영: {active_session.live_ops.selected_profile().title} | 레인: {current_live_ops.lane_id}"
        if active_session.codex_strategy.custom_instruction.strip():
            strategy_text += "\n추가 지시: " + active_session.codex_strategy.custom_instruction.strip()
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
        recent_deep_decision = self.engine.recommend_deep_integration_mode(entry.session, entry.runtime)
        recent_deep_mode = get_deep_integration_mode_option(recent_deep_decision.effective_mode_id)
        recent_live_ops = self.engine.recommend_live_ops_status(entry.session, entry.runtime)
        recent_strategy_text = (
            f"운영 프로필: {recent_strategy.title} | 선택 mode: {entry.session.codex_strategy.selected_mode().title} | "
            f"실제 launch: {recent_mode.title}"
        )
        recent_strategy_text += (
            f"\nDeep integration: {recent_deep_mode.title} | supervisor: {recent_deep_decision.supervisor_state}"
        )
        recent_strategy_text += f"\n라이브 운영: {entry.session.live_ops.selected_profile().title} | 레인: {recent_live_ops.lane_id}"
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
        self._refresh_project_home(self.session)
        self._refresh_codex_strategy_panel(self.session)
        self._refresh_judgment_panel(self.session)
        self._refresh_visual_panel(self.session)
        self._refresh_voice_panel(self.session)
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
        self.deep_integration_mode_var.set(
            self._deep_integration_mode_label_for_id(self.session.deep_integration.selected_mode_id)
        )
        self.deep_app_server_readiness_var.set(
            self._deep_integration_readiness_label_for_id(self.session.deep_integration.app_server_readiness_id)
        )
        self.deep_cloud_trigger_readiness_var.set(
            self._deep_integration_readiness_label_for_id(self.session.deep_integration.cloud_trigger_readiness_id)
        )
        self.deep_fallback_allowed_var.set(self.session.deep_integration.desktop_fallback_allowed)
        self.live_ops_profile_var.set(self._live_ops_profile_label_for_id(self.session.live_ops.selected_profile_id))
        self.live_ops_report_var.set(self._live_ops_report_label_for_id(self.session.live_ops.report_cadence_id))
        self.live_ops_reentry_var.set(self._live_ops_reentry_label_for_id(self.session.live_ops.reentry_mode_id))
        self.live_ops_max_steps_var.set(str(self.session.live_ops.max_unattended_steps))
        self.judgment_engine_mode_var.set(self._judgment_mode_label_for_id(self.session.judgment.engine_mode_id))
        self.judgment_model_name_var.set(self.session.judgment.model_name)
        self.judgment_confidence_var.set(str(self.session.judgment.confidence_threshold))
        self.visual_target_mode_var.set(self._visual_target_label_for_id(self.session.visual.target_mode_id))
        self.visual_capture_scope_var.set(self._visual_scope_label_for_id(self.session.visual.capture_scope_id))
        self.visual_retention_var.set(self._visual_retention_label_for_id(self.session.visual.retention_hint_id))
        self.visual_sensitive_risk_var.set(self.session.visual.sensitive_content_risk)
        self.voice_language_var.set(self.session.voice.language_code)
        self.voice_microphone_var.set(self.session.voice.microphone_name)
        self.voice_speaker_var.set(self.session.voice.speaker_name)
        self.voice_auto_brief_var.set(self.session.voice.auto_brief_enabled)
        self.voice_confirmation_var.set(self.session.voice.confirmation_enabled)
        self.voice_spoken_feedback_var.set(self.session.voice.spoken_feedback_enabled)
        self.voice_ambient_ready_var.set(self.session.voice.ambient_ready_enabled)
        self._set_scrolled_text(self.codex_strategy_note, self.session.codex_strategy.custom_instruction)
        self.deep_app_server_notes_var.set(self.session.deep_integration.app_server_notes)
        self.deep_cloud_trigger_notes_var.set(self.session.deep_integration.cloud_trigger_notes)
        self._set_scrolled_text(self.deep_handoff_note, self.session.deep_integration.handoff_notes)
        self._set_scrolled_text(self.live_ops_note, self.session.live_ops.operator_note)
        self._set_scrolled_text(self.visual_expected_page, self.session.visual.expected_page)
        self._set_scrolled_text(self.visual_focus, self.session.visual.observation_focus_text)
        self._set_scrolled_text(self.visual_expected_signals, self.session.visual.expected_signals_text)
        self._set_scrolled_text(self.visual_disallowed_signals, self.session.visual.disallowed_signals_text)
        self._set_scrolled_text(self.visual_observed_notes, self.session.visual.observed_notes_text)
        self._set_scrolled_text(self.voice_transcript_input, self.runtime.voice_last_transcript)
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
        self._refresh_judgment_panel(self.session)
        self._refresh_visual_panel(self.session)
        self._refresh_voice_panel(self.session)
        self._refresh_popup_shell()

    def _collect_session(self) -> SessionConfig:
        session = SessionConfig.from_dict(self.session.to_dict())
        session.project.project_summary = self.project_summary.get("1.0", END).strip()
        session.project.target_outcome = self.target_outcome.get("1.0", END).strip()
        session.project.steps_text = self.steps_text.get("1.0", END).strip()
        session.codex_strategy.selected_preset_id = self._current_codex_strategy_preset_id()
        session.codex_strategy.selected_mode_id = self._current_codex_mode_id()
        session.codex_strategy.custom_instruction = self.codex_strategy_note.get("1.0", END).strip()
        session.deep_integration.selected_mode_id = self._current_deep_integration_mode_id()
        session.deep_integration.app_server_readiness_id = self._current_app_server_readiness_id()
        session.deep_integration.cloud_trigger_readiness_id = self._current_cloud_trigger_readiness_id()
        session.deep_integration.desktop_fallback_allowed = bool(self.deep_fallback_allowed_var.get())
        session.deep_integration.app_server_notes = self.deep_app_server_notes_var.get().strip()
        session.deep_integration.cloud_trigger_notes = self.deep_cloud_trigger_notes_var.get().strip()
        session.deep_integration.handoff_notes = self.deep_handoff_note.get("1.0", END).strip()
        session.live_ops.selected_profile_id = self._current_live_ops_profile_id()
        session.live_ops.report_cadence_id = self._current_live_ops_report_id()
        session.live_ops.reentry_mode_id = self._current_live_ops_reentry_id()
        session.live_ops.max_unattended_steps = max(1, int(self.live_ops_max_steps_var.get().strip() or "3"))
        session.live_ops.operator_note = self.live_ops_note.get("1.0", END).strip()
        session.judgment.engine_mode_id = self._current_judgment_engine_mode_id()
        session.judgment.model_name = self.judgment_model_name_var.get().strip() or session.judgment.model_name
        session.judgment.confidence_threshold = float(self.judgment_confidence_var.get().strip() or "0.6")
        session.visual.target_mode_id = self._current_visual_target_mode_id()
        session.visual.capture_scope_id = self._current_visual_scope_id()
        session.visual.retention_hint_id = self._current_visual_retention_id()
        session.visual.sensitive_content_risk = self.visual_sensitive_risk_var.get().strip() or "medium"
        session.visual.expected_page = self.visual_expected_page.get("1.0", END).strip()
        session.visual.observation_focus_text = self.visual_focus.get("1.0", END).strip()
        session.visual.expected_signals_text = self.visual_expected_signals.get("1.0", END).strip()
        session.visual.disallowed_signals_text = self.visual_disallowed_signals.get("1.0", END).strip()
        session.visual.observed_notes_text = self.visual_observed_notes.get("1.0", END).strip()
        session.voice.language_code = self.voice_language_var.get().strip() or session.voice.language_code
        session.voice.microphone_name = self.voice_microphone_var.get().strip()
        session.voice.speaker_name = self.voice_speaker_var.get().strip()
        session.voice.auto_brief_enabled = bool(self.voice_auto_brief_var.get())
        session.voice.confirmation_enabled = bool(self.voice_confirmation_var.get())
        session.voice.spoken_feedback_enabled = bool(self.voice_spoken_feedback_var.get())
        session.voice.ambient_ready_enabled = bool(self.voice_ambient_ready_var.get())

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
        base_state = self.engine.build_surface_state(
            self.session,
            self.runtime,
            preview=self._current_preview,
            queue=self._current_queue,
        )
        self._surface_state = self.engine.apply_judgment_surface_overlay(
            base_state,
            self.session,
            self.runtime,
            preview=self._current_preview,
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
        self._refresh_codex_strategy_panel(self.session)
        self._refresh_judgment_panel(self.session)
        self._refresh_visual_panel(self.session)
        self._refresh_voice_panel(self.session)
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
