# Visual Evidence Contract v1

## 목적

Phase 5에서 `무엇을 캡처하고 무엇을 읽게 할지`를 judgment 입력과 같은 수준으로 안정적으로 고정합니다.

## 왜 필요한가

화면 인식은 강력하지만, 아무 규칙 없이 붙이면 아래 문제가 생깁니다.

- 불필요한 전체 화면 캡처 증가
- 민감 정보 저장 위험
- 시각 근거와 현재 단계 문맥이 분리
- 모델이 무엇을 봐야 하는지 애매해짐

그래서 Phase 5에서는 `visual evidence packet`을 공통 계약으로 둡니다.

## 최상위 구조

```json
{
  "capture_plan": {},
  "expected_state": {},
  "observation_focus": [],
  "screen_targets": [],
  "judgment_bridge": {},
  "safety": {}
}
```

## 1. capture_plan

무엇을 왜 캡처하는지 정의합니다.

예시 필드:

- `capture_reason`
- `priority`
- `trigger`
- `requested_by`

## 2. expected_state

지금 화면이 ideally 어떤 상태여야 하는지 적습니다.

예시 필드:

- `current_step_title`
- `expected_page`
- `expected_signals`
- `disallowed_signals`

## 3. observation_focus

모델이 길게 설명하지 말고 먼저 확인해야 할 포인트 목록입니다.

예시:

- 오류 배너가 있는가
- 핵심 CTA가 보이는가
- 빈 화면인가
- Codex 주장과 모순되는 신호가 있는가

## 4. screen_targets

실제로 읽을 화면 대상들입니다.

각 대상은 아래 필드를 가질 수 있습니다.

- `target_type`
  - `codex_window`
  - `browser_result`
  - `error_region`
  - `dialog`
- `path`
- `region_label`
- `why_this_target`

## 5. judgment_bridge

Phase 4 판단 루프와 다시 연결하기 위한 문맥입니다.

예시 필드:

- `current_decision_before_visual`
- `why_visual_is_needed`
- `question_to_resolve`
- `candidate_outcomes`

## 6. safety

시각 입력 안전 기준입니다.

예시 필드:

- `capture_scope`
- `sensitive_content_risk`
- `retention_hint`
- `fallback_if_uncertain`

## 최소 패킷 예시

```json
{
  "capture_plan": {
    "capture_reason": "Codex는 완료라고 했지만 브라우저 결과 확인이 필요함",
    "priority": "high",
    "trigger": "claim_screen_mismatch",
    "requested_by": "javis"
  },
  "expected_state": {
    "current_step_title": "브라우저 결과 확인",
    "expected_page": "성공 페이지 또는 정상 렌더링 화면",
    "expected_signals": ["핵심 CTA 표시", "오류 배너 없음"],
    "disallowed_signals": ["빈 화면", "오류 배너", "잘못된 라우팅"]
  },
  "observation_focus": [
    "오류 배너 존재 여부",
    "핵심 CTA 존재 여부",
    "Codex 주장과 모순되는 신호"
  ],
  "screen_targets": [
    {
      "target_type": "browser_result",
      "path": "runtime/captures/browser-001.png",
      "region_label": "main browser viewport",
      "why_this_target": "실제 결과 확인용"
    }
  ],
  "judgment_bridge": {
    "current_decision_before_visual": "continue",
    "why_visual_is_needed": "텍스트 근거만으로는 결과 검증이 부족함",
    "question_to_resolve": "정말 성공 화면이 맞는가",
    "candidate_outcomes": ["continue", "retry", "ask_user"]
  },
  "safety": {
    "capture_scope": "targeted_only",
    "sensitive_content_risk": "medium",
    "retention_hint": "short",
    "fallback_if_uncertain": "ask_user"
  }
}
```

## v1 구현 원칙

- 전체 화면보다 타깃 캡처 우선
- 설명보다 판정 중심
- 시각 입력은 Phase 4 판단 루프에 다시 연결
- 애매하면 continue보다 ask_user / pause 우선
