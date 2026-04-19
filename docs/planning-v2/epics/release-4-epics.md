# Release 4 Epics

## Epic R4-A. Judgment Foundation

### 목적

현재 상태를 OpenAI 판단 엔진에 안정적으로 넣고, 구조화 응답을 안전하게 검증하는 바닥을 만듭니다.

### 주요 산출물

- judgment packet builder
- judgment prompt assembly
- structured response validator

### 포함 티켓

- `R4-001`
- `R4-002`
- `R4-003`

## Epic R4-B. Decision UX & Routing

### 목적

판단 결과를 상단장님이 바로 이해할 수 있게 보여주고, continue / retry / ask_user를 제품 행동과 연결합니다.

### 주요 산출물

- judgment surface
- rejudge flow
- decision action router

### 포함 티켓

- `R4-004`
- `R4-005`

## Epic R4-C. Safety, History & Readiness

### 목적

왜 이런 판단이 나왔는지 추적 가능하게 하고, 확신/위험 기준을 제품 안에 고정해 Release 4를 반복 검증 가능한 상태로 마감합니다.

### 주요 산출물

- judgment timeline / evidence digest
- confidence / risk guard
- Release 4 smoke suite

### 포함 티켓

- `R4-006`
- `R4-007`
- `R4-008`

## 에픽 순서

1. `R4-A`
2. `R4-B`
3. `R4-C`

이 순서의 이유는 먼저 `무엇을 어떻게 판단할지`와 `응답을 어떻게 믿을지`가 정리돼야, 그 다음에야 `UI와 실제 후속 행동`을 안전하게 연결할 수 있기 때문입니다.
