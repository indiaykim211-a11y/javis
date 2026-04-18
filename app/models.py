from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


DEFAULT_RULES = """- 한 번에 안정적으로 끝낼 수 있는 범위만 진행해 주세요.
- 작업이 끝나면 짧은 검증 결과를 같이 남겨 주세요.
- 막히면 임시 우회가 아니라 원인을 먼저 설명해 주세요."""


@dataclass
class ProjectContext:
    project_summary: str = ""
    target_outcome: str = ""
    operator_rules: str = DEFAULT_RULES
    steps_text: str = ""

    def steps(self) -> list[str]:
        return [line.strip() for line in self.steps_text.splitlines() if line.strip()]


@dataclass
class WindowTarget:
    title_contains: str = "Codex"
    process_name: str = "Codex"
    last_handle: int | None = None
    last_process_id: int | None = None
    last_title: str = ""
    last_process_name: str = ""
    last_score: int = 0
    last_reason: str = ""

    def remember_success(
        self,
        *,
        handle: int,
        process_id: int,
        title: str,
        process_name: str,
        score: int,
        reason: str,
    ) -> None:
        self.last_handle = handle
        self.last_process_id = process_id
        self.last_title = title
        self.last_process_name = process_name
        self.last_score = score
        self.last_reason = reason

    def clear_lock(self) -> None:
        self.last_handle = None
        self.last_process_id = None
        self.last_title = ""
        self.last_process_name = ""
        self.last_score = 0
        self.last_reason = ""


@dataclass
class AutomationConfig:
    poll_interval_sec: int = 8
    stable_cycles_required: int = 3
    min_seconds_between_actions: int = 45
    signature_threshold: float = 0.018
    input_click_x: int = 350
    input_click_y: int = 760
    input_click_reference_width: int | None = None
    input_click_reference_height: int | None = None
    calibration_delay_sec: int = 3
    calibration_test_text: str = "[Jarvis calibration] input focus test"
    submit_with_enter: bool = True
    dry_run: bool = True

    def remember_calibration(
        self,
        *,
        offset_x: int,
        offset_y: int,
        window_width: int,
        window_height: int,
    ) -> None:
        self.input_click_x = offset_x
        self.input_click_y = offset_y
        self.input_click_reference_width = window_width
        self.input_click_reference_height = window_height

    def resolve_click_offset(
        self,
        *,
        actual_width: int | None = None,
        actual_height: int | None = None,
    ) -> tuple[int, int]:
        if (
            actual_width
            and actual_height
            and self.input_click_reference_width
            and self.input_click_reference_height
            and self.input_click_reference_width > 0
            and self.input_click_reference_height > 0
        ):
            scaled_x = round(self.input_click_x * actual_width / self.input_click_reference_width)
            scaled_y = round(self.input_click_y * actual_height / self.input_click_reference_height)
            clamped_x = min(max(scaled_x, 0), max(actual_width - 1, 0))
            clamped_y = min(max(scaled_y, 0), max(actual_height - 1, 0))
            return clamped_x, clamped_y
        return self.input_click_x, self.input_click_y

    def calibration_summary(self) -> str:
        if self.input_click_reference_width and self.input_click_reference_height:
            return (
                f"저장 좌표 ({self.input_click_x}, {self.input_click_y}) "
                f"@ {self.input_click_reference_width}x{self.input_click_reference_height}"
            )
        return f"저장 좌표 ({self.input_click_x}, {self.input_click_y})"


@dataclass
class SessionConfig:
    project: ProjectContext = field(default_factory=ProjectContext)
    window: WindowTarget = field(default_factory=WindowTarget)
    automation: AutomationConfig = field(default_factory=AutomationConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionConfig":
        project = ProjectContext(**data.get("project", {}))
        window = WindowTarget(**data.get("window", {}))
        automation = AutomationConfig(**data.get("automation", {}))
        return cls(project=project, window=window, automation=automation)


@dataclass
class RuntimeState:
    next_step_index: int = 0
    stable_cycles: int = 0
    last_signature: str | None = None
    last_capture_path: str | None = None
    last_action_at: float = 0.0
    auto_running: bool = False
    last_target_title: str = ""
    last_target_reason: str = ""
    last_target_score: int | None = None
    target_lock_status: str = ""

    def reset_stability(self) -> None:
        self.stable_cycles = 0
        self.last_signature = None


@dataclass
class CycleReport:
    window_found: bool
    window_title: str = ""
    capture_path: str | None = None
    stable_cycles: int = 0
    signature_distance: float | None = None
    action_taken: bool = False
    step_sent: str | None = None
    message: str = ""
    target_reason: str = ""
    target_score: int | None = None
    lock_status: str = ""
