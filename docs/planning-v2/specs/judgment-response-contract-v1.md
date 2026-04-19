# Judgment Response Contract v1

## 문서 목적

이 문서는 OpenAI 판단 엔진과 로컬 런타임 사이에서 주고받는 구조화 응답 계약을 정의합니다.

이 계약은 아래 두 문제를 막기 위해 필요합니다.

- 모델이 자유롭게 말해서 자동화가 흔들리는 문제
- UI와 실행 로직이 응답을 안정적으로 해석하지 못하는 문제

## 기본 원칙

- 응답은 항상 JSON 객체 1개여야 합니다.
- 허용된 enum만 사용해야 합니다.
- 필수 필드가 빠지면 로컬 런타임은 `pause`로 처리합니다.
- 설명 텍스트는 짧고 UI 친화적이어야 합니다.

## 최상위 스키마

```json
{
  "decision": "continue",
  "reason": "현재 단계 산출이 최소 기준을 충족했고 위험 신호가 낮습니다.",
  "confidence": 0.82,
  "risk_level": "low",
  "message_to_user": "다음 단계로 진행할 수 있습니다.",
  "needs_user_confirmation": false,
  "next_prompt_to_codex": null,
  "evidence_summary": [
    "최근 변화량이 안정화 기준 이내입니다.",
    "현재 단계 목표가 충족된 것으로 보입니다."
  ],
  "follow_up_actions": [
    "advance_step"
  ]
}
```

## 필드 정의

### `decision`

필수 필드입니다.

허용값:

- `continue`
- `wait`
- `retry`
- `pause`
- `ask_user`

의미:

- `continue`
  - 다음 단계 진행 가능
- `wait`
  - 아직 관찰 지속
- `retry`
  - 같은 단계 보정 지시 필요
- `pause`
  - 자동 진행 중지
- `ask_user`
  - 상단장님 판단 필요

### `reason`

필수 필드입니다.

- 내부 판단 근거를 한두 문장으로 설명
- 로그와 운영 기록에 남는 기준 텍스트

### `confidence`

필수 필드입니다.

- 0.0 ~ 1.0
- 판단 확신도

권장 해석:

- `0.80 이상`
  - 비교적 강한 확신
- `0.60 ~ 0.79`
  - 조건부 진행 가능
- `0.59 이하`
  - 자동 진행에 보수적으로 대응

### `risk_level`

필수 필드입니다.

허용값:

- `low`
- `medium`
- `high`

### `message_to_user`

필수 필드입니다.

- Assistant Popup에서 바로 보여줄 짧은 문장
- 상단장님 관점 기준 설명

좋은 예:

- “조금 더 기다리는 편이 안전합니다.”
- “다음 단계 진행 준비가 됐습니다.”
- “판단 확신이 낮아 확인이 필요합니다.”

### `needs_user_confirmation`

필수 필드입니다.

- `true`
- `false`

`ask_user`에서는 보통 `true`여야 합니다.

### `next_prompt_to_codex`

선택 필드지만, `retry`에서는 사실상 필수입니다.

- Codex에 다시 보낼 짧고 명확한 재지시
- 필요 없으면 `null`

### `evidence_summary`

권장 필드입니다.

- 판단 근거를 리스트로 요약
- 로그 및 디버깅에 유용

### `follow_up_actions`

권장 필드입니다.

허용 예시:

- `advance_step`
- `keep_observing`
- `send_repair_prompt`
- `pause_automation`
- `notify_user`

## 로컬 런타임 검증 규칙

### 1) 허용되지 않은 decision

- 자동으로 `pause`

### 2) confidence 누락

- 자동으로 `pause`

### 3) high risk인데 continue

- 자동으로 `ask_user` 또는 `pause`로 강등

### 4) retry인데 next_prompt_to_codex 없음

- 자동으로 `ask_user`

### 5) message_to_user 비어 있음

- 기본 문구로 대체

## UI 매핑 규칙

### `continue`

- 상태 배지: `진행 가능`
- 기본 액션: `진행`

### `wait`

- 상태 배지: `관찰 중`
- 기본 액션: `대기`

### `retry`

- 상태 배지: `보정 필요`
- 기본 액션: `재지시`

### `pause`

- 상태 배지: `중지`
- 기본 액션: `설정`

### `ask_user`

- 상태 배지: `확인 필요`
- 기본 액션: `상단장님 확인`

## 예시 응답

### 1) 계속 기다려야 하는 경우

```json
{
  "decision": "wait",
  "reason": "최근 화면 변화가 아직 남아 있어 현재 단계 완료로 보기 이릅니다.",
  "confidence": 0.77,
  "risk_level": "low",
  "message_to_user": "조금 더 지켜보는 편이 안전합니다.",
  "needs_user_confirmation": false,
  "next_prompt_to_codex": null,
  "evidence_summary": [
    "최근 변화량이 아직 존재합니다."
  ],
  "follow_up_actions": [
    "keep_observing"
  ]
}
```

### 2) 같은 단계 보정이 필요한 경우

```json
{
  "decision": "retry",
  "reason": "현재 산출은 일부 완료됐지만 목표 수준을 아직 충족하지 못했습니다.",
  "confidence": 0.81,
  "risk_level": "medium",
  "message_to_user": "같은 단계를 한 번 더 보정하는 것이 좋겠습니다.",
  "needs_user_confirmation": false,
  "next_prompt_to_codex": "현재 단계 결과를 기준에 맞게 보정해 주세요. 변경 후 검증 결과도 짧게 남겨 주세요.",
  "evidence_summary": [
    "목표 대비 미완 요소가 남아 있습니다."
  ],
  "follow_up_actions": [
    "send_repair_prompt"
  ]
}
```

### 3) 상단장님 확인이 필요한 경우

```json
{
  "decision": "ask_user",
  "reason": "위험 신호는 높지 않지만 현재 증거만으로는 합격 여부 판단 확신이 부족합니다.",
  "confidence": 0.48,
  "risk_level": "medium",
  "message_to_user": "판단 확신이 낮아 상단장님 확인이 필요합니다.",
  "needs_user_confirmation": true,
  "next_prompt_to_codex": null,
  "evidence_summary": [
    "현재 입력만으로 결과 품질 판단이 애매합니다."
  ],
  "follow_up_actions": [
    "notify_user"
  ]
}
```

## 한 줄 결론

`javis`의 판단 엔진은 말 잘하는 모델이 아니라, 엄격한 계약 아래에서 안정적으로 결정을 내려주는 구조화 의사결정 모듈이어야 합니다.
