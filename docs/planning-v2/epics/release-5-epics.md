# Release 5 Epics

## Epic R5-A. Visual Evidence Foundation

### 목적

시각 증거를 아무렇게나 읽지 않고, 어떤 화면을 왜 캡처하고 어떻게 판단 입력으로 묶을지 바닥을 만듭니다.

### 주요 산출물

- capture target planner
- visual evidence packet builder
- browser / Codex observation prompts

### 포함 티켓

- `R5-001`
- `R5-002`
- `R5-003`

## Epic R5-B. Visual Decision UX & Contradiction Handling

### 목적

화면에서 읽은 근거를 상단장님이 바로 이해할 수 있게 보여주고, Codex 주장과 실제 화면의 모순을 제품 행동으로 연결합니다.

### 주요 산출물

- visual summary surface
- claim vs screen contradiction detector
- visual rejudge bridge

### 포함 티켓

- `R5-004`
- `R5-005`
- `R5-006`

## Epic R5-C. Capture Safety & Readiness

### 목적

민감한 화면이나 과한 캡처를 제어하고, Release 5를 반복 검증 가능한 상태로 마감합니다.

### 주요 산출물

- privacy / capture safety guard
- Release 5 smoke suite

### 포함 티켓

- `R5-007`
- `R5-008`

## 에픽 순서

1. `R5-A`
2. `R5-B`
3. `R5-C`

이 순서의 이유는 먼저 `어떤 화면을 왜 읽을지`가 정리돼야, 그 다음에야 `그 화면을 어떻게 해석하고 제품 행동으로 연결할지`를 안정적으로 설계할 수 있기 때문입니다.
