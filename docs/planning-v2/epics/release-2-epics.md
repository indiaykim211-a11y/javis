# Release 2 Epics

## Epic R2-A. Codex Strategy Surface

### 목적

Codex-first 전략을 문서가 아니라 `앱 안에서 바로 선택하고 이해할 수 있는 표면`으로 끌어올립니다.

### 주요 산출물

- Codex 전략 센터
- 시나리오 프리셋 선택기
- 프로젝트 기준 prompt 초안 미리보기

### 포함 티켓

- `R2-001`
- `R2-002`

## Epic R2-B. Project Operating Profile

### 목적

프로젝트마다 어떤 Codex 운영 방식을 쓸지 기억하고, 나중에 다시 불러와도 같은 운영 맥락을 이어갈 수 있게 만듭니다.

### 주요 산출물

- 프로젝트별 Codex 운영 프로필
- worktree / cadence / notes 저장 기초
- 런북 / handoff 패널

### 포함 티켓

- `R2-003`
- `R2-004`

## Epic R2-C. Native-vs-Fallback Readiness

### 목적

Codex 네이티브 기능과 로컬 데스크톱 제어의 경계를 분명히 해서, 제품이 다시 클릭 자동화 앱으로 되돌아가지 않게 만듭니다.

### 주요 산출물

- native vs fallback 안전 매트릭스
- Release 2 스모크 스위트

### 포함 티켓

- `R2-005`
- `R2-006`

## 에픽 순서

권장 순서는 아래와 같습니다.

1. `R2-A`
2. `R2-B`
3. `R2-C`

이 순서의 이유는 먼저 `전략이 보여야` 운영 프로필을 저장할 의미가 생기고, 그다음에야 native/fallback 경계를 제품적으로 점검할 수 있기 때문입니다.
