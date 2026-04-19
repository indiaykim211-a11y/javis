# Judgment Input Contract v1

## 문서 목적

이 문서는 로컬 런타임이 OpenAI 판단 엔진에 어떤 정보를 어떤 구조로 넣어야 하는지 정의합니다.

이 계약이 필요한 이유는 아래와 같습니다.

- 입력이 매번 제각각이면 판단 결과가 흔들립니다.
- 너무 많은 원문을 넣으면 비용과 지연이 커집니다.
- 화면 인식이 붙기 전과 후를 같은 구조로 이어가려면 공통 입력 틀이 필요합니다.

## 기본 원칙

- 입력은 항상 구조화된 JSON 객체 1개를 기준으로 합니다.
- 텍스트 원문을 무제한으로 넣지 않고, 먼저 요약/정규화합니다.
- 이미지가 있더라도 JSON 안에 큰 바이너리를 넣지 않습니다.
- 판단에 필요한 최소 정보만 넣고, 실행은 로컬 런타임이 담당합니다.

## 최상위 스키마

```json
{
  "schema_version": "judgment-input-v1",
  "cycle_context": {},
  "project_context": {},
  "runtime_context": {},
  "policy_context": {},
  "evidence_context": {},
  "user_override_context": {},
  "attachments": []
}
```

## 최상위 필드 정의

### `schema_version`

필수 필드입니다.

- 현재 값: `judgment-input-v1`

### `cycle_context`

필수 필드입니다.

- 이번 판단 사이클 자체를 식별하는 메타데이터

### `project_context`

필수 필드입니다.

- 현재 프로젝트와 단계 정보

### `runtime_context`

필수 필드입니다.

- 자동화 엔진의 현재 상태와 최근 액션

### `policy_context`

필수 필드입니다.

- 상단장님 정책과 시스템 안전 규칙

### `evidence_context`

필수 필드입니다.

- 현재 판단에 사용할 증거 요약

### `user_override_context`

필수 필드입니다.

- 수동 승인, 강제 보류, 최근 피드백 같은 사람 개입 정보

### `attachments`

선택 필드입니다.

- 스크린샷, 나중에는 오디오 같은 비텍스트 입력의 첨부 메타데이터

## 1. Cycle Context

```json
{
  "session_id": "sess_001",
  "project_id": "proj_alpha",
  "cycle_id": "cycle_20260418_210001",
  "timestamp": "2026-04-18T21:00:01+09:00",
  "mode": "text_only"
}
```

### 필드 설명

- `session_id`
  - 현재 앱 세션 식별자
- `project_id`
  - 최근 프로젝트/현재 프로젝트 식별자
- `cycle_id`
  - 판단 1회를 구분하는 id
- `timestamp`
  - ISO 8601 형식 권장
- `mode`
  - `text_only`
  - `text_plus_vision`
  - 나중에는 `text_plus_vision_plus_voice`

## 2. Project Context

```json
{
  "project_summary": "Codex 기반 데스크톱 어시스턴트 앱 개발",
  "target_outcome": "Assistant Alpha 완성",
  "total_steps": 12,
  "current_step_index": 4,
  "current_step_title": "Assistant Popup 상태 카드 구현",
  "current_step_goal": "팝업에서 상태, 이유, 다음 행동을 보여준다.",
  "previous_step_title": "기본 팝업 레이아웃 구성",
  "next_step_title": "설정창 분리",
  "remaining_steps_preview": [
    "설정창 분리",
    "세션 복원 진입점 추가",
    "상태 배지 시스템 연결"
  ],
  "current_prompt_preview": "이전 단계가 끝났다면..."
}
```

### 필수/권장 필드

- 필수
  - `project_summary`
  - `target_outcome`
  - `total_steps`
  - `current_step_index`
  - `current_step_title`
- 권장
  - `current_step_goal`
  - `previous_step_title`
  - `next_step_title`
  - `remaining_steps_preview`
  - `current_prompt_preview`

### 정규화 규칙

- 전체 단계 목록을 통째로 넣기보다 `현재 + 직전 1개 + 다음 3개` 정도로 압축
- 프롬프트 원문은 길면 요약본과 핵심 원문만 유지

## 3. Runtime Context

```json
{
  "automation_mode": "auto",
  "dry_run": false,
  "auto_running": true,
  "last_action_type": "wait",
  "seconds_since_last_action": 38,
  "stable_cycles": 3,
  "target_window_found": true,
  "target_lock_status": "이전 성공 창 유지",
  "failure_count_recent": 0,
  "retry_count_current_step": 1,
  "last_decision": "wait",
  "last_decision_confidence": 0.71
}
```

### 필수 필드

- `automation_mode`
  - `manual`
  - `auto`
- `dry_run`
- `auto_running`
- `seconds_since_last_action`
- `stable_cycles`
- `target_window_found`

### 권장 필드

- `last_action_type`
- `target_lock_status`
- `failure_count_recent`
- `retry_count_current_step`
- `last_decision`
- `last_decision_confidence`

### 주의점

- 로컬 메트릭은 있는 그대로 주되, 모델에게 너무 기술적인 내부 구현 세부사항을 쏟아붓지 않음
- 숫자는 해석 가능한 수준으로만 전달

## 4. Policy Context

```json
{
  "master_policy": "확신이 낮으면 멈추고 설명한다.",
  "progress_policy": "현재 단계 목표 충족 시에만 continue 가능",
  "vision_policy": "화면 이상 신호가 있으면 high risk로 간주",
  "repair_policy": "재지시는 짧고 명확하게 한 번에 한 수정 요청만",
  "report_policy": "상단장님께는 결론 우선의 짧은 존댓말로 보고",
  "safety_policy": "위험도가 높거나 확신이 낮으면 ask_user 또는 pause",
  "policy_revision": "2026-04-18.01"
}
```

### 필수 필드

- `master_policy`
- `progress_policy`
- `safety_policy`

### 권장 필드

- `vision_policy`
- `repair_policy`
- `report_policy`
- `policy_revision`

### 정규화 규칙

- 정책 전문이 매우 길면 요약본 우선
- 필요 시 원문은 별도 참조로 유지하되, 판단 입력에는 핵심만 삽입

## 5. Evidence Context

```json
{
  "codex_state_summary": "최근 20초 동안 응답 변화가 줄었고 마지막 출력은 구현 완료와 검증 통과를 언급함",
  "browser_state_summary": null,
  "screen_summary": null,
  "log_excerpt": [
    "현재 단계 프롬프트 생성 완료",
    "화면 안정화 카운트 3"
  ],
  "anomalies": [],
  "capture_signature_distance": 0.013,
  "latest_capture_path": "C:/.../captures/codex-20260418-210001.bmp",
  "evidence_confidence": 0.74
}
```

### v1 필수 필드

- `codex_state_summary`
- `log_excerpt`
- `anomalies`

### v1 권장 필드

- `capture_signature_distance`
- `latest_capture_path`
- `evidence_confidence`

### Release 3 이후 확장 필드

- `screen_summary`
- `browser_state_summary`
- `ocr_summary`
- `vision_findings`

### 정규화 규칙

- 로그 원문 전체 대신 최근 핵심 3~10줄만 전달
- 캡처 경로 자체보다 캡처에서 읽은 요약이 더 중요
- anomalies는 문자열 리스트로 정리

## 6. User Override Context

```json
{
  "manual_approval_granted": false,
  "manual_pause_requested": false,
  "preferred_aggressiveness": "conservative",
  "recent_user_feedback": [
    "애매하면 다음 단계로 넘기지 말 것"
  ],
  "temporary_override_note": ""
}
```

### 필수 필드

- `manual_approval_granted`
- `manual_pause_requested`

### 권장 필드

- `preferred_aggressiveness`
  - `conservative`
  - `balanced`
  - `aggressive`
- `recent_user_feedback`
- `temporary_override_note`

## 7. Attachments

```json
[
  {
    "type": "image",
    "role": "codex_capture",
    "path": "C:/.../captures/codex-20260418-210001.bmp",
    "summary": "Codex 데스크톱 캡처",
    "include_in_model_input": true
  }
]
```

### 원칙

- JSON에는 첨부 메타데이터만 넣음
- 실제 이미지는 모델 API가 허용하는 방식으로 별도 첨부
- `include_in_model_input = true`인 첨부만 실제 요청에 포함

### 향후 확장

- `role = browser_capture`
- `role = diff_capture`
- 나중에는 `type = audio`

## 필수 검증 규칙

### 1) 단계 인덱스 범위 검증

- `current_step_index`는 `0 <= index < total_steps`

### 2) text_only 모드 검증

- `mode = text_only`인데 vision 전용 필드가 필수처럼 들어가면 안 됨

### 3) manual pause 우선

- `manual_pause_requested = true`면 모델이 `continue`를 내더라도 실행하지 않음

### 4) current step 없음

- 현재 단계가 없으면 판단 요청 자체를 보내지 않거나, 별도 종료 상태로 처리

## 토큰/길이 관리 원칙

### 1) 단계 정보 압축

- 전체 단계를 전부 넣지 말고 현재 판단에 필요한 범위만 유지

### 2) 로그 압축

- 로그 전체 원문 금지
- 최근 핵심 라인만 추출

### 3) 화면 정보 압축

- OCR/비전 원문 전체 대신 요약 우선

### 4) 정책 압축

- 판단에 필요한 핵심 규칙만 삽입

## 예시 1: Release 2용 텍스트 중심 입력

```json
{
  "schema_version": "judgment-input-v1",
  "cycle_context": {
    "session_id": "sess_01",
    "project_id": "proj_assistant_alpha",
    "cycle_id": "cycle_104",
    "timestamp": "2026-04-18T21:15:00+09:00",
    "mode": "text_only"
  },
  "project_context": {
    "project_summary": "javis Assistant Alpha 구현",
    "target_outcome": "작은 팝업 어시스턴트 완성",
    "total_steps": 8,
    "current_step_index": 2,
    "current_step_title": "상태 카드 문구 연결",
    "current_step_goal": "현재 상태, 이유, 다음 행동을 팝업에 보여준다.",
    "previous_step_title": "팝업 레이아웃 구성",
    "next_step_title": "설정창 분리",
    "remaining_steps_preview": [
      "설정창 분리",
      "세션 복원 진입점 연결"
    ],
    "current_prompt_preview": "이전 단계가 끝났다면..."
  },
  "runtime_context": {
    "automation_mode": "auto",
    "dry_run": false,
    "auto_running": true,
    "last_action_type": "wait",
    "seconds_since_last_action": 42,
    "stable_cycles": 3,
    "target_window_found": true,
    "target_lock_status": "이전 성공 창 유지",
    "failure_count_recent": 0,
    "retry_count_current_step": 0,
    "last_decision": "wait",
    "last_decision_confidence": 0.72
  },
  "policy_context": {
    "master_policy": "확신이 낮으면 멈추고 설명한다.",
    "progress_policy": "현재 단계 목표 충족 시에만 다음 단계 진행",
    "safety_policy": "확신 낮으면 ask_user 또는 wait",
    "report_policy": "짧은 존댓말, 결론 우선",
    "policy_revision": "2026-04-18.01"
  },
  "evidence_context": {
    "codex_state_summary": "최근 로그상 구현 완료와 검증 통과를 언급했습니다.",
    "browser_state_summary": null,
    "screen_summary": null,
    "log_excerpt": [
      "상태 카드 구현 완료",
      "간단한 검증 통과"
    ],
    "anomalies": [],
    "capture_signature_distance": 0.011,
    "latest_capture_path": "C:/.../captures/codex-1.bmp",
    "evidence_confidence": 0.79
  },
  "user_override_context": {
    "manual_approval_granted": false,
    "manual_pause_requested": false,
    "preferred_aggressiveness": "conservative",
    "recent_user_feedback": [
      "애매하면 다음으로 넘기지 말기"
    ],
    "temporary_override_note": ""
  },
  "attachments": []
}
```

## 예시 2: Release 3용 화면 포함 입력

```json
{
  "schema_version": "judgment-input-v1",
  "cycle_context": {
    "session_id": "sess_02",
    "project_id": "proj_visual_beta",
    "cycle_id": "cycle_201",
    "timestamp": "2026-05-02T11:40:00+09:00",
    "mode": "text_plus_vision"
  },
  "project_context": {
    "project_summary": "브라우저 결과까지 읽는 javis",
    "target_outcome": "Visual Beta",
    "total_steps": 14,
    "current_step_index": 7,
    "current_step_title": "브라우저 레이아웃 검증",
    "current_step_goal": "모바일 레이아웃 이상 여부를 판단한다.",
    "previous_step_title": "Codex 수정 적용",
    "next_step_title": "재수정 또는 합격 처리",
    "remaining_steps_preview": [
      "재수정 또는 합격 처리",
      "결과 요약"
    ],
    "current_prompt_preview": "브라우저 결과를 검토해 주세요."
  },
  "runtime_context": {
    "automation_mode": "auto",
    "dry_run": false,
    "auto_running": true,
    "last_action_type": "observe",
    "seconds_since_last_action": 18,
    "stable_cycles": 2,
    "target_window_found": true,
    "target_lock_status": "현재 후보 선택",
    "failure_count_recent": 1,
    "retry_count_current_step": 1,
    "last_decision": "retry",
    "last_decision_confidence": 0.66
  },
  "policy_context": {
    "master_policy": "화면 품질이 애매하면 사람 확인을 우선한다.",
    "progress_policy": "결과 화면이 목표 기준을 충족할 때만 continue",
    "vision_policy": "레이아웃 깨짐, 미완 로딩, 오류 배너를 주요 이상 신호로 간주",
    "repair_policy": "원인 중심, 한 번에 한 수정 지시",
    "report_policy": "짧고 단정한 한국어 존댓말",
    "safety_policy": "위험 높으면 pause 또는 ask_user",
    "policy_revision": "2026-05-02.03"
  },
  "evidence_context": {
    "codex_state_summary": "Codex는 수정 완료를 보고했습니다.",
    "browser_state_summary": "모바일 화면 하단 카드 정렬이 어긋나 보입니다.",
    "screen_summary": "브라우저 캡처에서 하단 영역 레이아웃 불일치 가능성이 있습니다.",
    "log_excerpt": [
      "브라우저 캡처 저장 완료",
      "모바일 기준 QA 시작"
    ],
    "anomalies": [
      "mobile_layout_misalignment_possible"
    ],
    "capture_signature_distance": 0.024,
    "latest_capture_path": "C:/.../captures/browser-qa-1.bmp",
    "evidence_confidence": 0.68
  },
  "user_override_context": {
    "manual_approval_granted": false,
    "manual_pause_requested": false,
    "preferred_aggressiveness": "balanced",
    "recent_user_feedback": [
      "모바일 품질은 엄격하게 보기"
    ],
    "temporary_override_note": ""
  },
  "attachments": [
    {
      "type": "image",
      "role": "browser_capture",
      "path": "C:/.../captures/browser-qa-1.bmp",
      "summary": "모바일 브라우저 캡처",
      "include_in_model_input": true
    }
  ]
}
```

## 한 줄 결론

`javis`의 판단 입력은 많이 넣는 것이 중요한 게 아니라, 현재 단계 판단에 필요한 정보를 안정적으로 정리해서 일관된 구조로 넣는 것이 중요합니다.
