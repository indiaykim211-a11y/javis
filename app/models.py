from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SESSION_SCHEMA_VERSION = 1


DEFAULT_MASTER_POLICY = """- 한 번에 안정적으로 끝낼 수 있는 범위만 진행해 주세요.
- 작업이 끝나면 짧은 검증 결과를 같이 남겨 주세요.
- 막히면 임시 우회가 아니라 원인을 먼저 설명해 주세요."""

DEFAULT_PROGRESS_POLICY = """- 현재 단계가 목표를 충족할 때만 다음 단계로 진행해 주세요.
- 결과가 애매하면 바로 다음 단계로 넘기지 말고 보류 또는 재확인을 선택해 주세요.
- 한 번에 한 단계만 진행하고, 어떤 검증을 했는지 짧게 남겨 주세요."""

DEFAULT_VISION_POLICY = """- 화면이나 캡처가 주어지면 Codex 설명과 실제 결과가 일치하는지 먼저 확인해 주세요.
- 오류 문구, 브라우저 결과, 빌드 상태, 입력창 위치 같은 실증 신호를 우선 읽어 주세요.
- 확신이 낮으면 추정이라고 명시하고 추가 확인이 필요하다고 알려 주세요."""

DEFAULT_REPAIR_POLICY = """- 문제가 보이면 원인, 재현 단서, 원하는 수정 방향을 짧고 구체적으로 정리해 다시 지시해 주세요.
- 수정 요청은 한 번에 안정적으로 처리 가능한 범위로 나누어 주세요.
- 같은 실패가 반복되면 무한 재시도하지 말고 보류 또는 사람 확인으로 넘겨 주세요."""

DEFAULT_REPORT_POLICY = """- 상단장님께는 현재 상태, 핵심 변화, 위험 요소, 다음 행동을 짧고 명확하게 보고해 주세요.
- 필요한 경우에만 상세 로그나 파일 경로를 덧붙여 주세요.
- 장황한 설명보다 바로 판단 가능한 운영 요약을 우선해 주세요."""

DEFAULT_SAFETY_POLICY = """- 애매하면 진행보다 보류를 우선해 주세요.
- 반복 실패, 삭제 위험, 배포 위험, 과금 위험처럼 되돌리기 어려운 신호가 보이면 자동 진행을 멈춰 주세요.
- 사용자 승인 없이 파괴적이거나 되돌리기 어려운 행동을 유도하지 말아 주세요."""

DEFAULT_RULES = DEFAULT_MASTER_POLICY

POLICY_SECTION_SPECS: tuple[tuple[str, str, str], ...] = (
    ("master_policy", "운영 마스터", "프로젝트 전반 원칙과 기본 톤을 정의합니다."),
    ("progress_policy", "단계 진행", "계속 진행할지, 보류할지, 재확인할지 기준을 적습니다."),
    ("vision_policy", "화면 판독", "스크린샷과 실제 화면을 읽을 때 우선순위를 적습니다."),
    ("repair_policy", "보정 지시", "문제 발견 시 재지시 방식과 수정 범위를 적습니다."),
    ("report_policy", "사용자 보고", "상단장님께 어떤 톤과 형식으로 보고할지 적습니다."),
    ("safety_policy", "안전 규칙", "위험, 반복 실패, 애매한 상황에서 멈추는 기준을 적습니다."),
)

DEFAULT_POLICY_TEMPLATES: dict[str, str] = {
    "master_policy": DEFAULT_MASTER_POLICY,
    "progress_policy": DEFAULT_PROGRESS_POLICY,
    "vision_policy": DEFAULT_VISION_POLICY,
    "repair_policy": DEFAULT_REPAIR_POLICY,
    "report_policy": DEFAULT_REPORT_POLICY,
    "safety_policy": DEFAULT_SAFETY_POLICY,
}


@dataclass
class ProjectContext:
    project_summary: str = ""
    target_outcome: str = ""
    operator_rules: str = DEFAULT_RULES
    steps_text: str = ""

    def steps(self) -> list[str]:
        return [line.strip() for line in self.steps_text.splitlines() if line.strip()]


@dataclass(frozen=True)
class CodexAutomationPreset:
    preset_id: str
    title: str
    automation_type: str
    cadence_hint: str
    worktree_hint: str
    summary: str
    use_when: str
    codex_role: str
    javis_role: str
    prompt_template: str


@dataclass(frozen=True)
class CodexAutomationModeOption:
    mode_id: str
    title: str
    summary: str
    result_location: str


@dataclass(frozen=True)
class CodexAutomationModeDecision:
    recommended_mode_id: str
    recommended_reason: str
    effective_mode_id: str
    effective_reason: str
    cadence_hint: str
    worktree_hint: str
    result_location: str
    waiting_for: str
    next_follow_up: str


CODEX_AUTOMATION_MODE_OPTIONS: tuple[CodexAutomationModeOption, ...] = (
    CodexAutomationModeOption(
        mode_id="recommended",
        title="추천값 따르기",
        summary="현재 프로젝트와 선택한 프리셋 기준으로 javis가 가장 맞는 운영 방식을 고릅니다.",
        result_location="추천된 운영 방식에 따라 같은 스레드 또는 Triage로 안내됩니다.",
    ),
    CodexAutomationModeOption(
        mode_id="no_automation",
        title="no automation | 같은 스레드 순차 진행",
        summary="시간 기반 heartbeat 없이 현재 스레드에서 단계나 티켓을 순차적으로 이어 갑니다.",
        result_location="현재 Codex 운영 스레드에서 바로 결과를 다시 확인합니다.",
    ),
    CodexAutomationModeOption(
        mode_id="thread_automation",
        title="thread automation | 같은 스레드 heartbeat",
        summary="같은 대화 문맥을 유지한 채 주기적 follow-up이나 재확인이 필요할 때 씁니다.",
        result_location="현재 스레드와 해당 thread heartbeat 결과를 다시 확인합니다.",
    ),
    CodexAutomationModeOption(
        mode_id="project_automation",
        title="project automation | 독립 실행",
        summary="nightly brief, smoke, triage처럼 독립 실행 보고가 더 자연스러운 작업에 씁니다.",
        result_location="Codex Automations pane / Triage에서 독립 실행 결과를 확인합니다.",
    ),
)


CODEX_AUTOMATION_PRESETS: tuple[CodexAutomationPreset, ...] = (
    CodexAutomationPreset(
        preset_id="masterplan_followup",
        title="마스터플랜 Follow-up Heartbeat",
        automation_type="thread automation",
        cadence_hint="같은 스레드에서 15~30분 heartbeat 권장",
        worktree_hint="보통 worktree 불필요",
        summary="마스터플랜을 이미 세운 뒤, 같은 대화 문맥을 이어가며 다음 단계 진행 여부를 계속 확인하는 운영 방식입니다.",
        use_when="현재 스레드 문맥을 유지한 채 다음 단계 진행, 보류, 재지시를 이어가고 싶을 때",
        codex_role="현재 스레드 문맥을 읽고 지금 단계 상태를 파악한 뒤, 계속 진행 가능한지 판단합니다.",
        javis_role="상태 요약, 시나리오 선택, 후속 프롬프트 준비, 필요 시 사람 확인 흐름을 덮습니다.",
        prompt_template="""이 스레드를 기준으로 현재 프로젝트 마스터플랜 진행 상태를 계속 추적해 주세요.

핵심 원칙:
- 한 번에 한 단계만 다룹니다.
- 완료 기준이 충족될 때만 다음 단계로 넘어갑니다.
- 애매하면 보류하고 이유를 짧게 남깁니다.
- 현재 단계에서 필요한 검증이나 확인이 있으면 같이 적어 주세요.

보고 형식:
1. 현재 상태
2. 진행 또는 보류 판단
3. 다음 액션
4. 위험 또는 확인 필요 사항""",
    ),
    CodexAutomationPreset(
        preset_id="release_smoke",
        title="Release Smoke 자동 점검",
        automation_type="project automation",
        cadence_hint="릴리즈 직후 또는 필요 시 반복 실행",
        worktree_hint="코드 변경 가능성이 있으면 background worktree 권장",
        summary="릴리즈 직후 기본 실행 흐름이 살아 있는지 빠르게 점검하는 운영 방식입니다.",
        use_when="릴리즈나 주요 UI 변경 직후 기본 동작을 점검하고 싶을 때",
        codex_role="스모크 체크리스트나 스크립트를 실행하고 실패 지점을 짧게 요약합니다.",
        javis_role="어떤 스모크를 돌릴지 제안하고, 결과를 운영자 시점으로 정리합니다.",
        prompt_template="""현재 프로젝트의 기본 릴리즈 스모크를 실행하고 결과를 짧게 정리해 주세요.

핵심 원칙:
- 먼저 빠른 스모크 기준부터 확인합니다.
- 실패 시 가장 먼저 막힌 지점과 재현 단서를 남깁니다.
- 자동 수정은 명확하고 안전한 경우에만 제안합니다.

보고 형식:
1. 실행한 스모크
2. 통과/실패 요약
3. 실패한 경우 원인 후보
4. 다음 액션""",
    ),
    CodexAutomationPreset(
        preset_id="nightly_brief",
        title="Nightly Project Brief",
        automation_type="standalone / project automation",
        cadence_hint="매일 밤 1회 또는 평일 저녁 1회",
        worktree_hint="보통 worktree 선택 권장",
        summary="하루 동안의 변화, 남은 위험, 다음 작업 후보를 밤마다 자동 정리하는 운영 방식입니다.",
        use_when="하루 작업을 정리하고 다음날 바로 이어갈 준비를 하고 싶을 때",
        codex_role="당일 변화, 열린 이슈, 위험 요소, 내일 우선순위를 정리합니다.",
        javis_role="요약 형식과 운영자 보고 톤을 고정해 줍니다.",
        prompt_template="""현재 프로젝트 상태를 기준으로 짧은 nightly brief를 만들어 주세요.

핵심 원칙:
- 오늘 바뀐 점을 먼저 요약합니다.
- 아직 남아 있는 위험과 막힘을 숨기지 않습니다.
- 내일 바로 이어갈 수 있는 우선순위 3개를 뽑아 주세요.

보고 형식:
1. 오늘의 변화
2. 현재 위험
3. 내일 우선순위
4. 보류 또는 확인 필요""",
    ),
    CodexAutomationPreset(
        preset_id="pr_babysit",
        title="PR Babysitting",
        automation_type="thread automation 또는 project automation + skill",
        cadence_hint="PR 오픈 중 주기적 follow-up",
        worktree_hint="코드 수정 가능성이 있으면 worktree 권장",
        summary="PR 상태, 리뷰 코멘트, 다음 대응을 주기적으로 확인하는 운영 방식입니다.",
        use_when="코드 리뷰 대응과 PR 추적을 꾸준히 이어가고 싶을 때",
        codex_role="리뷰 피드백, 상태 변화, 필요한 후속 액션을 찾아 정리합니다.",
        javis_role="운영 우선순위와 보고 형식을 정리하고, 대응 흐름을 이어붙입니다.",
        prompt_template="""현재 PR 또는 관련 작업 상태를 추적하고 다음 대응이 필요한지 확인해 주세요.

핵심 원칙:
- 새 리뷰, 새 실패, 새 요청사항이 있으면 먼저 정리합니다.
- 바로 대응 가능한 것과 사람 확인이 필요한 것을 구분합니다.
- 중복 대응은 피하고, 가장 중요한 변화만 남겨 주세요.

보고 형식:
1. 새 변화
2. 필요한 대응
3. 바로 처리 가능 여부
4. 상단장님 확인 필요 사항""",
    ),
    CodexAutomationPreset(
        preset_id="ci_failure_triage",
        title="CI Failure Triage",
        automation_type="project automation",
        cadence_hint="실패 감지 후 즉시 또는 1시간 단위 재확인",
        worktree_hint="수정 가능성이 높아 worktree 권장",
        summary="CI 실패가 났을 때 원인 후보와 다음 액션을 빠르게 좁히는 운영 방식입니다.",
        use_when="테스트나 빌드 실패를 사람 대신 먼저 분류해 주길 원할 때",
        codex_role="실패 로그, 최근 변경, 재현 단서를 바탕으로 원인 후보를 정리합니다.",
        javis_role="위험도를 분류하고, 무한 재시도 대신 보류/수정/사람 호출 기준을 붙입니다.",
        prompt_template="""현재 CI 또는 빌드 실패를 triage해 주세요.

핵심 원칙:
- 실패한 지점과 최근 변경의 연결고리를 먼저 찾습니다.
- 확신이 낮으면 추정이라고 명시합니다.
- 바로 수정 가능한지, 사람 확인이 필요한지 구분합니다.

보고 형식:
1. 실패 지점
2. 원인 후보
3. 바로 수정 가능 여부
4. 다음 액션""",
    ),
    CodexAutomationPreset(
        preset_id="recent_code_bugfix",
        title="Recent Code Self-Bugfix",
        automation_type="project automation + skill",
        cadence_hint="최근 변경 직후 또는 회귀 의심 시 실행",
        worktree_hint="코드 수정이 포함되므로 worktree 권장",
        summary="최근 바뀐 코드에서 바로 드러난 회귀나 오류를 빠르게 복구하는 운영 방식입니다.",
        use_when="방금 바꾼 코드 주변에서 오류가 보이고, 먼저 안전한 수정 후보를 얻고 싶을 때",
        codex_role="최근 변경과 실패 신호를 연결해 안전한 수정 후보를 제안하거나 구현합니다.",
        javis_role="수정 범위를 좁히고, 과감한 자동 수정 대신 안전한 단위로 다시 쪼개도록 안내합니다.",
        prompt_template="""최근 변경된 코드 주변에서 발생한 오류를 우선 triage하고, 안전하면 작은 수정 단위로 해결해 주세요.

핵심 원칙:
- 최근 변경 범위를 먼저 좁힙니다.
- 한 번에 안정적으로 끝낼 수 있는 작은 수정만 시도합니다.
- 위험하면 바로 보류하고 사람 확인으로 넘깁니다.

보고 형식:
1. 문제 요약
2. 최근 변경과의 연결
3. 수정 또는 보류 판단
4. 다음 액션""",
    ),
)

DEFAULT_CODEX_STRATEGY_PRESET_ID = CODEX_AUTOMATION_PRESETS[0].preset_id
DEFAULT_CODEX_AUTOMATION_MODE_ID = CODEX_AUTOMATION_MODE_OPTIONS[0].mode_id
DEFAULT_JUDGMENT_MODEL_NAME = "gpt-5.4-mini"
DEFAULT_JUDGMENT_ENGINE_MODE_ID = "auto"
DEFAULT_JUDGMENT_CONFIDENCE_THRESHOLD = 0.6
DEFAULT_VISUAL_TARGET_MODE_ID = "auto"
DEFAULT_VISUAL_CAPTURE_SCOPE_ID = "targeted_only"
DEFAULT_VISUAL_RETENTION_HINT_ID = "short"
DEFAULT_VISUAL_SENSITIVE_RISK = "medium"
DEFAULT_VOICE_LANGUAGE = "ko-KR"


def get_codex_automation_preset(preset_id: str) -> CodexAutomationPreset:
    for preset in CODEX_AUTOMATION_PRESETS:
        if preset.preset_id == preset_id:
            return preset
    return CODEX_AUTOMATION_PRESETS[0]


def get_codex_automation_mode_option(mode_id: str) -> CodexAutomationModeOption:
    for option in CODEX_AUTOMATION_MODE_OPTIONS:
        if option.mode_id == mode_id:
            return option
    return CODEX_AUTOMATION_MODE_OPTIONS[0]


@dataclass(frozen=True)
class JudgmentEngineModeOption:
    mode_id: str
    title: str
    summary: str


JUDGMENT_ENGINE_MODE_OPTIONS: tuple[JudgmentEngineModeOption, ...] = (
    JudgmentEngineModeOption(
        mode_id="auto",
        title="자동 | OpenAI 가능하면 사용, 없으면 규칙 기반",
        summary="API 키와 환경이 준비되면 OpenAI 판단을 시도하고, 아니면 안전한 규칙 기반 판단으로 내려옵니다.",
    ),
    JudgmentEngineModeOption(
        mode_id="rule_based",
        title="규칙 기반 프리뷰",
        summary="현재 프로젝트 상태와 운영 모드, 최근 로그를 바탕으로 로컬 규칙 기반 판단만 수행합니다.",
    ),
)


def get_judgment_engine_mode_option(mode_id: str) -> JudgmentEngineModeOption:
    for option in JUDGMENT_ENGINE_MODE_OPTIONS:
        if option.mode_id == mode_id:
            return option
    return JUDGMENT_ENGINE_MODE_OPTIONS[0]


@dataclass(frozen=True)
class VisualTargetModeOption:
    mode_id: str
    title: str
    summary: str


VISUAL_TARGET_MODE_OPTIONS: tuple[VisualTargetModeOption, ...] = (
    VisualTargetModeOption(
        mode_id="auto",
        title="자동 | 필요할 때만 시각 확인",
        summary="현재 단계, 판단 결과, 최근 로그를 보고 Codex 창 또는 브라우저 결과 화면 중 무엇을 읽을지 고릅니다.",
    ),
    VisualTargetModeOption(
        mode_id="codex_window",
        title="Codex 창 우선",
        summary="Codex 화면과 최근 캡처를 기준으로 시각 근거를 먼저 읽습니다.",
    ),
    VisualTargetModeOption(
        mode_id="browser_result",
        title="브라우저 결과 화면 우선",
        summary="브라우저 결과 화면, CTA, 오류 배너, 렌더링 상태를 먼저 읽습니다.",
    ),
)


def get_visual_target_mode_option(mode_id: str) -> VisualTargetModeOption:
    for option in VISUAL_TARGET_MODE_OPTIONS:
        if option.mode_id == mode_id:
            return option
    return VISUAL_TARGET_MODE_OPTIONS[0]


@dataclass(frozen=True)
class VisualCaptureScopeOption:
    scope_id: str
    title: str
    summary: str


VISUAL_CAPTURE_SCOPE_OPTIONS: tuple[VisualCaptureScopeOption, ...] = (
    VisualCaptureScopeOption(
        scope_id="targeted_only",
        title="타깃 캡처만",
        summary="전체 화면 대신 현재 판단에 필요한 창이나 영역만 읽습니다.",
    ),
    VisualCaptureScopeOption(
        scope_id="full_if_needed",
        title="필요 시 전체도 허용",
        summary="기본은 타깃 캡처지만, 근거가 부족할 때만 더 넓은 화면을 허용합니다.",
    ),
)


def get_visual_capture_scope_option(scope_id: str) -> VisualCaptureScopeOption:
    for option in VISUAL_CAPTURE_SCOPE_OPTIONS:
        if option.scope_id == scope_id:
            return option
    return VISUAL_CAPTURE_SCOPE_OPTIONS[0]


@dataclass(frozen=True)
class VisualRetentionOption:
    retention_id: str
    title: str
    summary: str


VISUAL_RETENTION_OPTIONS: tuple[VisualRetentionOption, ...] = (
    VisualRetentionOption(
        retention_id="short",
        title="짧게 유지",
        summary="현재 판단과 직전 비교에 필요한 정도로만 짧게 유지합니다.",
    ),
    VisualRetentionOption(
        retention_id="session_only",
        title="세션 동안만 유지",
        summary="현재 세션이 끝날 때까지만 시각 증거를 유지합니다.",
    ),
)


def get_visual_retention_option(retention_id: str) -> VisualRetentionOption:
    for option in VISUAL_RETENTION_OPTIONS:
        if option.retention_id == retention_id:
            return option
    return VISUAL_RETENTION_OPTIONS[0]


@dataclass
class CodexStrategyConfig:
    selected_preset_id: str = DEFAULT_CODEX_STRATEGY_PRESET_ID
    selected_mode_id: str = DEFAULT_CODEX_AUTOMATION_MODE_ID
    custom_instruction: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CodexStrategyConfig":
        return cls(
            selected_preset_id=data.get("selected_preset_id", DEFAULT_CODEX_STRATEGY_PRESET_ID),
            selected_mode_id=data.get("selected_mode_id", DEFAULT_CODEX_AUTOMATION_MODE_ID),
            custom_instruction=data.get("custom_instruction", ""),
        )

    def selected_preset(self) -> CodexAutomationPreset:
        return get_codex_automation_preset(self.selected_preset_id)

    def selected_mode(self) -> CodexAutomationModeOption:
        return get_codex_automation_mode_option(self.selected_mode_id)


@dataclass
class JudgmentConfig:
    engine_mode_id: str = DEFAULT_JUDGMENT_ENGINE_MODE_ID
    model_name: str = DEFAULT_JUDGMENT_MODEL_NAME
    confidence_threshold: float = DEFAULT_JUDGMENT_CONFIDENCE_THRESHOLD
    max_history_items: int = 8

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JudgmentConfig":
        return cls(
            engine_mode_id=data.get("engine_mode_id", DEFAULT_JUDGMENT_ENGINE_MODE_ID),
            model_name=data.get("model_name", DEFAULT_JUDGMENT_MODEL_NAME),
            confidence_threshold=float(data.get("confidence_threshold", DEFAULT_JUDGMENT_CONFIDENCE_THRESHOLD) or 0.0),
            max_history_items=int(data.get("max_history_items", 8) or 8),
        )

    def selected_mode(self) -> JudgmentEngineModeOption:
        return get_judgment_engine_mode_option(self.engine_mode_id)


@dataclass
class JudgmentResult:
    decision: str = ""
    reason: str = ""
    confidence: float = 0.0
    risk_level: str = "medium"
    message_to_user: str = ""
    needs_user_confirmation: bool = False
    next_prompt_to_codex: str | None = None
    evidence_summary: list[str] = field(default_factory=list)
    follow_up_actions: list[str] = field(default_factory=list)
    source: str = ""
    validation_notes: list[str] = field(default_factory=list)
    evaluated_at: str = ""
    raw_response: str = ""

    @property
    def has_result(self) -> bool:
        return bool(self.decision or self.reason or self.evaluated_at)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JudgmentResult":
        return cls(
            decision=data.get("decision", ""),
            reason=data.get("reason", ""),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            risk_level=data.get("risk_level", "medium"),
            message_to_user=data.get("message_to_user", ""),
            needs_user_confirmation=bool(data.get("needs_user_confirmation", False)),
            next_prompt_to_codex=data.get("next_prompt_to_codex"),
            evidence_summary=[str(item) for item in data.get("evidence_summary", []) if str(item).strip()],
            follow_up_actions=[str(item) for item in data.get("follow_up_actions", []) if str(item).strip()],
            source=data.get("source", ""),
            validation_notes=[str(item) for item in data.get("validation_notes", []) if str(item).strip()],
            evaluated_at=data.get("evaluated_at", ""),
            raw_response=data.get("raw_response", ""),
        )


@dataclass
class JudgmentHistoryEntry:
    timestamp: str = ""
    decision: str = ""
    confidence: float = 0.0
    risk_level: str = "medium"
    source: str = ""
    message_to_user: str = ""
    reason: str = ""

    def display_line(self) -> str:
        decision = self.decision or "unknown"
        confidence_text = f"{self.confidence:.2f}"
        stamp = self.timestamp.replace("T", " ") if self.timestamp else "시각 없음"
        return f"[{stamp}] {decision} | conf {confidence_text} | risk {self.risk_level} | {self.message_to_user or self.reason}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JudgmentHistoryEntry":
        return cls(
            timestamp=data.get("timestamp", ""),
            decision=data.get("decision", ""),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            risk_level=data.get("risk_level", "medium"),
            source=data.get("source", ""),
            message_to_user=data.get("message_to_user", ""),
            reason=data.get("reason", ""),
        )


@dataclass
class VisualSupervisorConfig:
    target_mode_id: str = DEFAULT_VISUAL_TARGET_MODE_ID
    capture_scope_id: str = DEFAULT_VISUAL_CAPTURE_SCOPE_ID
    retention_hint_id: str = DEFAULT_VISUAL_RETENTION_HINT_ID
    sensitive_content_risk: str = DEFAULT_VISUAL_SENSITIVE_RISK
    expected_page: str = ""
    expected_signals_text: str = ""
    disallowed_signals_text: str = ""
    observation_focus_text: str = ""
    observed_notes_text: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VisualSupervisorConfig":
        return cls(
            target_mode_id=data.get("target_mode_id", DEFAULT_VISUAL_TARGET_MODE_ID),
            capture_scope_id=data.get("capture_scope_id", DEFAULT_VISUAL_CAPTURE_SCOPE_ID),
            retention_hint_id=data.get("retention_hint_id", DEFAULT_VISUAL_RETENTION_HINT_ID),
            sensitive_content_risk=data.get("sensitive_content_risk", DEFAULT_VISUAL_SENSITIVE_RISK),
            expected_page=data.get("expected_page", ""),
            expected_signals_text=data.get("expected_signals_text", ""),
            disallowed_signals_text=data.get("disallowed_signals_text", ""),
            observation_focus_text=data.get("observation_focus_text", ""),
            observed_notes_text=data.get("observed_notes_text", ""),
        )

    def target_mode(self) -> VisualTargetModeOption:
        return get_visual_target_mode_option(self.target_mode_id)

    def capture_scope(self) -> VisualCaptureScopeOption:
        return get_visual_capture_scope_option(self.capture_scope_id)

    def retention_hint(self) -> VisualRetentionOption:
        return get_visual_retention_option(self.retention_hint_id)

    def expected_signals(self) -> list[str]:
        return [line.strip("-• ").strip() for line in self.expected_signals_text.splitlines() if line.strip()]

    def disallowed_signals(self) -> list[str]:
        return [line.strip("-• ").strip() for line in self.disallowed_signals_text.splitlines() if line.strip()]

    def observation_focus(self) -> list[str]:
        return [line.strip("-• ").strip() for line in self.observation_focus_text.splitlines() if line.strip()]


@dataclass
class VisualEvidenceResult:
    target_type: str = ""
    target_label: str = ""
    contradiction_detected: bool = False
    contradiction_level: str = "none"
    contradiction_reason: str = ""
    expected_summary: str = ""
    observed_summary: str = ""
    decision_hint: str = "continue"
    message_to_user: str = ""
    evidence_summary: list[str] = field(default_factory=list)
    mismatch_signals: list[str] = field(default_factory=list)
    source: str = ""
    evaluated_at: str = ""
    raw_response: str = ""

    @property
    def has_result(self) -> bool:
        return bool(self.target_type or self.observed_summary or self.evaluated_at)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VisualEvidenceResult":
        return cls(
            target_type=data.get("target_type", ""),
            target_label=data.get("target_label", ""),
            contradiction_detected=bool(data.get("contradiction_detected", False)),
            contradiction_level=data.get("contradiction_level", "none"),
            contradiction_reason=data.get("contradiction_reason", ""),
            expected_summary=data.get("expected_summary", ""),
            observed_summary=data.get("observed_summary", ""),
            decision_hint=data.get("decision_hint", "continue"),
            message_to_user=data.get("message_to_user", ""),
            evidence_summary=[str(item) for item in data.get("evidence_summary", []) if str(item).strip()],
            mismatch_signals=[str(item) for item in data.get("mismatch_signals", []) if str(item).strip()],
            source=data.get("source", ""),
            evaluated_at=data.get("evaluated_at", ""),
            raw_response=data.get("raw_response", ""),
        )


@dataclass
class VisualEvidenceHistoryEntry:
    timestamp: str = ""
    target_label: str = ""
    contradiction_level: str = "none"
    decision_hint: str = "continue"
    message_to_user: str = ""

    def display_line(self) -> str:
        stamp = self.timestamp.replace("T", " ") if self.timestamp else "시각 없음"
        return f"[{stamp}] {self.target_label or 'target'} | {self.contradiction_level} | {self.decision_hint} | {self.message_to_user}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VisualEvidenceHistoryEntry":
        return cls(
            timestamp=data.get("timestamp", ""),
            target_label=data.get("target_label", ""),
            contradiction_level=data.get("contradiction_level", "none"),
            decision_hint=data.get("decision_hint", "continue"),
            message_to_user=data.get("message_to_user", ""),
        )


@dataclass
class VoiceConfig:
    language_code: str = DEFAULT_VOICE_LANGUAGE
    auto_brief_enabled: bool = True
    confirmation_enabled: bool = True
    spoken_feedback_enabled: bool = True
    ambient_ready_enabled: bool = False
    microphone_name: str = ""
    speaker_name: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoiceConfig":
        return cls(
            language_code=data.get("language_code", DEFAULT_VOICE_LANGUAGE),
            auto_brief_enabled=bool(data.get("auto_brief_enabled", True)),
            confirmation_enabled=bool(data.get("confirmation_enabled", True)),
            spoken_feedback_enabled=bool(data.get("spoken_feedback_enabled", True)),
            ambient_ready_enabled=bool(data.get("ambient_ready_enabled", False)),
            microphone_name=data.get("microphone_name", ""),
            speaker_name=data.get("speaker_name", ""),
        )


@dataclass
class VoiceCommandResult:
    transcript_text: str = ""
    normalized_intent_id: str = ""
    intent_confidence: float = 0.0
    action_id: str = ""
    action_status: str = ""
    message_to_user: str = ""
    spoken_briefing_text: str = ""
    clarification_question: str = ""
    requires_confirmation: bool = False
    source: str = ""
    evaluated_at: str = ""
    raw_response: str = ""

    @property
    def has_result(self) -> bool:
        return bool(self.transcript_text or self.normalized_intent_id or self.evaluated_at)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoiceCommandResult":
        return cls(
            transcript_text=data.get("transcript_text", ""),
            normalized_intent_id=data.get("normalized_intent_id", ""),
            intent_confidence=float(data.get("intent_confidence", 0.0) or 0.0),
            action_id=data.get("action_id", ""),
            action_status=data.get("action_status", ""),
            message_to_user=data.get("message_to_user", ""),
            spoken_briefing_text=data.get("spoken_briefing_text", ""),
            clarification_question=data.get("clarification_question", ""),
            requires_confirmation=bool(data.get("requires_confirmation", False)),
            source=data.get("source", ""),
            evaluated_at=data.get("evaluated_at", ""),
            raw_response=data.get("raw_response", ""),
        )


@dataclass
class VoiceHistoryEntry:
    timestamp: str = ""
    transcript_excerpt: str = ""
    intent_id: str = ""
    action_status: str = ""
    message_to_user: str = ""

    def display_line(self) -> str:
        stamp = self.timestamp.replace("T", " ") if self.timestamp else "시간 없음"
        excerpt = self.transcript_excerpt or "voice input"
        return f"[{stamp}] {self.intent_id or 'unknown'} | {self.action_status or 'pending'} | {excerpt}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoiceHistoryEntry":
        return cls(
            timestamp=data.get("timestamp", ""),
            transcript_excerpt=data.get("transcript_excerpt", ""),
            intent_id=data.get("intent_id", ""),
            action_status=data.get("action_status", ""),
            message_to_user=data.get("message_to_user", ""),
        )


@dataclass
class PolicyConfig:
    master_policy: str = DEFAULT_MASTER_POLICY
    progress_policy: str = DEFAULT_PROGRESS_POLICY
    vision_policy: str = DEFAULT_VISION_POLICY
    repair_policy: str = DEFAULT_REPAIR_POLICY
    report_policy: str = DEFAULT_REPORT_POLICY
    safety_policy: str = DEFAULT_SAFETY_POLICY
    edit_note: str = ""
    last_edited_at: str = ""
    last_edited_section: str = ""

    @classmethod
    def default_templates(cls) -> dict[str, str]:
        return dict(DEFAULT_POLICY_TEMPLATES)

    @classmethod
    def from_dict(cls, data: dict[str, Any], legacy_master_policy: str = "") -> "PolicyConfig":
        templates = cls.default_templates()
        master_policy = data.get("master_policy")
        if master_policy is None:
            master_policy = legacy_master_policy or templates["master_policy"]
        return cls(
            master_policy=master_policy,
            progress_policy=data.get("progress_policy", templates["progress_policy"]),
            vision_policy=data.get("vision_policy", templates["vision_policy"]),
            repair_policy=data.get("repair_policy", templates["repair_policy"]),
            report_policy=data.get("report_policy", templates["report_policy"]),
            safety_policy=data.get("safety_policy", templates["safety_policy"]),
            edit_note=data.get("edit_note", ""),
            last_edited_at=data.get("last_edited_at", ""),
            last_edited_section=data.get("last_edited_section", ""),
        )

    def section_text(self, section_key: str) -> str:
        return getattr(self, section_key, "")

    def set_section_text(self, section_key: str, text: str) -> None:
        setattr(self, section_key, text.strip())

    def section_label(self, section_key: str) -> str:
        for key, label, _description in POLICY_SECTION_SPECS:
            if key == section_key:
                return label
        return section_key

    def default_for(self, section_key: str) -> str:
        return DEFAULT_POLICY_TEMPLATES.get(section_key, "")

    def is_default_section(self, section_key: str) -> bool:
        return self.section_text(section_key).strip() == self.default_for(section_key).strip()

    def customized_section_count(self) -> int:
        return sum(0 if self.is_default_section(key) else 1 for key, _label, _description in POLICY_SECTION_SPECS)

    def build_rules_for_prompt(self) -> str:
        sections: list[str] = []
        for key, label, _description in POLICY_SECTION_SPECS:
            text = self.section_text(key).strip()
            if not text:
                continue
            sections.append(f"[{label}]")
            sections.append(text)
            sections.append("")
        return "\n".join(sections).strip()


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
    calibration_test_text: str = "[javis calibration] input focus test"
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
    codex_strategy: CodexStrategyConfig = field(default_factory=CodexStrategyConfig)
    judgment: JudgmentConfig = field(default_factory=JudgmentConfig)
    visual: VisualSupervisorConfig = field(default_factory=VisualSupervisorConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    window: WindowTarget = field(default_factory=WindowTarget)
    automation: AutomationConfig = field(default_factory=AutomationConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionConfig":
        project = ProjectContext(**data.get("project", {}))
        codex_strategy = CodexStrategyConfig.from_dict(data.get("codex_strategy", {}))
        judgment = JudgmentConfig.from_dict(data.get("judgment", {}))
        visual = VisualSupervisorConfig.from_dict(data.get("visual", {}))
        voice = VoiceConfig.from_dict(data.get("voice", {}))
        policy = PolicyConfig.from_dict(data.get("policy", {}), legacy_master_policy=project.operator_rules)
        project.operator_rules = policy.master_policy or DEFAULT_RULES
        window = WindowTarget(**data.get("window", {}))
        automation = AutomationConfig(**data.get("automation", {}))
        return cls(
            project=project,
            codex_strategy=codex_strategy,
            judgment=judgment,
            visual=visual,
            voice=voice,
            policy=policy,
            window=window,
            automation=automation,
        )


@dataclass
class StepQueueItem:
    index: int
    total: int
    title: str
    status: str

    def display_line(self) -> str:
        prefix = {
            "done": "[완료]",
            "current": "[현재]",
            "next": "[다음]",
            "upcoming": "[대기]",
        }.get(self.status, "[대기]")
        return f"{prefix} {self.index + 1}/{self.total} {self.title}"


@dataclass
class PromptPreview:
    step_index: int | None = None
    total_steps: int = 0
    step_title: str = ""
    generated_prompt: str = ""
    draft_prompt: str = ""
    is_dirty: bool = False
    is_complete: bool = False

    @property
    def has_step(self) -> bool:
        return self.step_index is not None and not self.is_complete

    @property
    def source_label(self) -> str:
        return "편집본" if self.is_dirty else "원문"


@dataclass
class PopupActionModel:
    action_id: str
    label: str
    enabled: bool = True
    emphasis: str = "secondary"


@dataclass
class SurfaceStateModel:
    state_key: str = "idle"
    project_label: str = ""
    badge_label: str = "준비"
    title: str = "대기 중"
    summary: str = ""
    reason: str = ""
    next_action: str = ""
    progress_label: str = ""
    detail_label: str = ""
    risk_label: str = "낮음"
    actions: list[PopupActionModel] = field(default_factory=list)


@dataclass
class RuntimeState:
    next_step_index: int = 0
    stable_cycles: int = 0
    last_signature: str | None = None
    last_capture_path: str | None = None
    last_action_at: float = 0.0
    auto_running: bool = False
    operator_paused: bool = False
    operator_pause_reason: str = ""
    last_target_title: str = ""
    last_target_reason: str = ""
    last_target_score: int | None = None
    target_lock_status: str = ""
    prompt_step_index: int | None = None
    prompt_generated: str = ""
    prompt_draft: str = ""
    prompt_dirty: bool = False
    last_judgment_packet: str = ""
    last_judgment_prompt: str = ""
    last_judgment_response: str = ""
    last_judgment: JudgmentResult = field(default_factory=JudgmentResult)
    judgment_history: list[JudgmentHistoryEntry] = field(default_factory=list)
    last_visual_packet: str = ""
    last_visual_prompt: str = ""
    last_visual_summary: str = ""
    last_visual_result: VisualEvidenceResult = field(default_factory=VisualEvidenceResult)
    visual_history: list[VisualEvidenceHistoryEntry] = field(default_factory=list)
    voice_capture_state: str = "idle"
    voice_pending_action_id: str = ""
    voice_pending_confirmation_text: str = ""
    voice_last_transcript: str = ""
    voice_last_briefing: str = ""
    last_voice_result: VoiceCommandResult = field(default_factory=VoiceCommandResult)
    voice_history: list[VoiceHistoryEntry] = field(default_factory=list)

    def reset_stability(self) -> None:
        self.stable_cycles = 0
        self.last_signature = None

    def sync_prompt_preview(self, step_index: int, generated_prompt: str) -> None:
        if self.prompt_step_index != step_index:
            self.prompt_step_index = step_index
            self.prompt_generated = generated_prompt
            self.prompt_draft = generated_prompt
            self.prompt_dirty = False
            return

        if self.prompt_generated != generated_prompt:
            self.prompt_generated = generated_prompt
            if not self.prompt_dirty:
                self.prompt_draft = generated_prompt

    def update_prompt_draft(self, draft_prompt: str) -> None:
        self.prompt_draft = draft_prompt
        self.prompt_dirty = draft_prompt != self.prompt_generated

    def clear_prompt_preview(self) -> None:
        self.prompt_step_index = None
        self.prompt_generated = ""
        self.prompt_draft = ""
        self.prompt_dirty = False

    def set_operator_pause(self, reason: str = "") -> None:
        self.operator_paused = True
        self.operator_pause_reason = reason

    def clear_operator_pause(self) -> None:
        self.operator_paused = False
        self.operator_pause_reason = ""

    def remember_judgment(
        self,
        result: JudgmentResult,
        *,
        packet_text: str,
        prompt_text: str,
        response_text: str,
        max_history_items: int,
    ) -> None:
        self.last_judgment = JudgmentResult.from_dict(result.to_dict())
        self.last_judgment_packet = packet_text
        self.last_judgment_prompt = prompt_text
        self.last_judgment_response = response_text
        history_entry = JudgmentHistoryEntry(
            timestamp=result.evaluated_at,
            decision=result.decision,
            confidence=result.confidence,
            risk_level=result.risk_level,
            source=result.source,
            message_to_user=result.message_to_user,
            reason=result.reason,
        )
        self.judgment_history.insert(0, history_entry)
        if max_history_items > 0:
            self.judgment_history = self.judgment_history[:max_history_items]

    def remember_visual_result(
        self,
        result: VisualEvidenceResult,
        *,
        packet_text: str,
        prompt_text: str,
        summary_text: str,
        max_history_items: int,
    ) -> None:
        self.last_visual_result = VisualEvidenceResult.from_dict(result.to_dict())
        self.last_visual_packet = packet_text
        self.last_visual_prompt = prompt_text
        self.last_visual_summary = summary_text
        history_entry = VisualEvidenceHistoryEntry(
            timestamp=result.evaluated_at,
            target_label=result.target_label,
            contradiction_level=result.contradiction_level,
            decision_hint=result.decision_hint,
            message_to_user=result.message_to_user,
        )
        self.visual_history.insert(0, history_entry)
        if max_history_items > 0:
            self.visual_history = self.visual_history[:max_history_items]

    def set_voice_pending_confirmation(self, action_id: str, text: str) -> None:
        self.voice_pending_action_id = action_id
        self.voice_pending_confirmation_text = text

    def clear_voice_pending_confirmation(self) -> None:
        self.voice_pending_action_id = ""
        self.voice_pending_confirmation_text = ""

    def remember_voice_result(
        self,
        result: VoiceCommandResult,
        *,
        max_history_items: int,
    ) -> None:
        self.last_voice_result = VoiceCommandResult.from_dict(result.to_dict())
        self.voice_last_transcript = result.transcript_text
        self.voice_last_briefing = result.spoken_briefing_text
        history_entry = VoiceHistoryEntry(
            timestamp=result.evaluated_at,
            transcript_excerpt=(result.transcript_text[:80] + "...") if len(result.transcript_text) > 80 else result.transcript_text,
            intent_id=result.normalized_intent_id,
            action_status=result.action_status,
            message_to_user=result.message_to_user,
        )
        self.voice_history.insert(0, history_entry)
        if max_history_items > 0:
            self.voice_history = self.voice_history[:max_history_items]

    def to_persisted_dict(self) -> dict[str, Any]:
        return {
            "next_step_index": self.next_step_index,
            "last_capture_path": self.last_capture_path,
            "last_action_at": self.last_action_at,
            "operator_paused": self.operator_paused,
            "operator_pause_reason": self.operator_pause_reason,
            "last_target_title": self.last_target_title,
            "last_target_reason": self.last_target_reason,
            "last_target_score": self.last_target_score,
            "target_lock_status": self.target_lock_status,
            "prompt_step_index": self.prompt_step_index,
            "prompt_generated": self.prompt_generated,
            "prompt_draft": self.prompt_draft,
            "prompt_dirty": self.prompt_dirty,
            "last_judgment_packet": self.last_judgment_packet,
            "last_judgment_prompt": self.last_judgment_prompt,
            "last_judgment_response": self.last_judgment_response,
            "last_judgment": self.last_judgment.to_dict(),
            "judgment_history": [item.to_dict() for item in self.judgment_history],
            "last_visual_packet": self.last_visual_packet,
            "last_visual_prompt": self.last_visual_prompt,
            "last_visual_summary": self.last_visual_summary,
            "last_visual_result": self.last_visual_result.to_dict(),
            "visual_history": [item.to_dict() for item in self.visual_history],
            "voice_capture_state": self.voice_capture_state,
            "voice_pending_action_id": self.voice_pending_action_id,
            "voice_pending_confirmation_text": self.voice_pending_confirmation_text,
            "voice_last_transcript": self.voice_last_transcript,
            "voice_last_briefing": self.voice_last_briefing,
            "last_voice_result": self.last_voice_result.to_dict(),
            "voice_history": [item.to_dict() for item in self.voice_history],
        }

    @classmethod
    def from_persisted_dict(cls, data: dict[str, Any]) -> "RuntimeState":
        score = data.get("last_target_score")
        prompt_step_index = data.get("prompt_step_index")
        return cls(
            next_step_index=int(data.get("next_step_index", 0) or 0),
            last_capture_path=data.get("last_capture_path") or None,
            last_action_at=float(data.get("last_action_at", 0.0) or 0.0),
            auto_running=False,
            operator_paused=bool(data.get("operator_paused", False)),
            operator_pause_reason=data.get("operator_pause_reason", ""),
            last_target_title=data.get("last_target_title", ""),
            last_target_reason=data.get("last_target_reason", ""),
            last_target_score=int(score) if score is not None else None,
            target_lock_status=data.get("target_lock_status", ""),
            prompt_step_index=int(prompt_step_index) if prompt_step_index is not None else None,
            prompt_generated=data.get("prompt_generated", ""),
            prompt_draft=data.get("prompt_draft", ""),
            prompt_dirty=bool(data.get("prompt_dirty", False)),
            last_judgment_packet=data.get("last_judgment_packet", ""),
            last_judgment_prompt=data.get("last_judgment_prompt", ""),
            last_judgment_response=data.get("last_judgment_response", ""),
            last_judgment=JudgmentResult.from_dict(data.get("last_judgment", {})),
            judgment_history=[
                JudgmentHistoryEntry.from_dict(item)
                for item in data.get("judgment_history", [])
                if isinstance(item, dict)
            ],
            last_visual_packet=data.get("last_visual_packet", ""),
            last_visual_prompt=data.get("last_visual_prompt", ""),
            last_visual_summary=data.get("last_visual_summary", ""),
            last_visual_result=VisualEvidenceResult.from_dict(data.get("last_visual_result", {})),
            visual_history=[
                VisualEvidenceHistoryEntry.from_dict(item)
                for item in data.get("visual_history", [])
                if isinstance(item, dict)
            ],
            voice_capture_state=data.get("voice_capture_state", "idle"),
            voice_pending_action_id=data.get("voice_pending_action_id", ""),
            voice_pending_confirmation_text=data.get("voice_pending_confirmation_text", ""),
            voice_last_transcript=data.get("voice_last_transcript", ""),
            voice_last_briefing=data.get("voice_last_briefing", ""),
            last_voice_result=VoiceCommandResult.from_dict(data.get("last_voice_result", {})),
            voice_history=[
                VoiceHistoryEntry.from_dict(item)
                for item in data.get("voice_history", [])
                if isinstance(item, dict)
            ],
        )


@dataclass
class RecentProjectEntry:
    project_key: str = ""
    project_summary: str = ""
    target_outcome: str = ""
    saved_at: str = ""
    next_step_index: int = 0
    total_steps: int = 0
    last_capture_path: str = ""
    session: SessionConfig = field(default_factory=SessionConfig)
    runtime: RuntimeState = field(default_factory=RuntimeState)

    def display_label(self) -> str:
        title = self.project_summary or self.target_outcome or "이름 없는 프로젝트"
        short_title = title if len(title) <= 28 else f"{title[:28]}..."
        progress_total = max(self.total_steps, 0)
        progress_current = min(self.next_step_index, progress_total)
        stamp = self.saved_at.replace("T", " ")[:16] if self.saved_at else "저장 시각 없음"
        return f"{stamp} | {short_title} ({progress_current}/{progress_total})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_key": self.project_key,
            "project_summary": self.project_summary,
            "target_outcome": self.target_outcome,
            "saved_at": self.saved_at,
            "next_step_index": self.next_step_index,
            "total_steps": self.total_steps,
            "last_capture_path": self.last_capture_path,
            "session": self.session.to_dict(),
            "runtime": self.runtime.to_persisted_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecentProjectEntry":
        return cls(
            project_key=data.get("project_key", ""),
            project_summary=data.get("project_summary", ""),
            target_outcome=data.get("target_outcome", ""),
            saved_at=data.get("saved_at", ""),
            next_step_index=int(data.get("next_step_index", 0) or 0),
            total_steps=int(data.get("total_steps", 0) or 0),
            last_capture_path=data.get("last_capture_path", ""),
            session=SessionConfig.from_dict(data.get("session", {})),
            runtime=RuntimeState.from_persisted_dict(data.get("runtime", {})),
        )


@dataclass
class PersistedSessionState:
    schema_version: int = SESSION_SCHEMA_VERSION
    saved_at: str = ""
    log_path: str = ""
    session: SessionConfig = field(default_factory=SessionConfig)
    runtime: RuntimeState = field(default_factory=RuntimeState)
    recent_projects: list[RecentProjectEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "saved_at": self.saved_at,
            "log_path": self.log_path,
            "session": self.session.to_dict(),
            "runtime": self.runtime.to_persisted_dict(),
            "recent_projects": [item.to_dict() for item in self.recent_projects],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersistedSessionState":
        schema_version = int(data.get("schema_version", SESSION_SCHEMA_VERSION) or SESSION_SCHEMA_VERSION)
        recent_projects = [
            RecentProjectEntry.from_dict(item)
            for item in data.get("recent_projects", [])
            if isinstance(item, dict)
        ]
        return cls(
            schema_version=schema_version,
            saved_at=data.get("saved_at", ""),
            log_path=data.get("log_path", ""),
            session=SessionConfig.from_dict(data.get("session", {})),
            runtime=RuntimeState.from_persisted_dict(data.get("runtime", {})),
            recent_projects=recent_projects,
        )


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
    step_index: int | None = None
    step_title: str = ""
    generated_prompt: str | None = None
    prompt_source: str = ""
