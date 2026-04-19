# Phase 7: Deep Integration

## 단계 목적

`Phase 7`은 `javis`가 Codex를 대신 실행하는 단계가 아니라, `Codex app / cloud / App Server / trigger` 같은 더 깊은 네이티브 연결점을 가장 잘 활용하는 단계입니다.

- 기본 전략은 계속 `Codex-first`입니다.
- `javis`는 계속 상위 감독, 핸드오프, 상태 통합, 위험 제어를 맡습니다.
- 데스크톱 클릭 자동화는 이 단계에서도 `fallback`으로만 남습니다.

## 왜 이 단계가 필요한가

`Phase 1~6`까지 오면 `javis`는 이미:

- 팝업/Control Center 기반 운영 표면
- Codex 전략 선택
- automation mode 판단
- judgment / visual / voice 감독

까지 갖추게 됩니다.

그다음 병목은 보통 기능 부족보다 `연결 깊이`에서 생깁니다.

- Codex app이 제공하는 네이티브 진입점이 더 생길 수 있음
- App Server 같은 직접 연결 방식이 실전 수준이 될 수 있음
- cloud trigger / background follow-up 성숙도가 올라갈 수 있음
- 여러 표면(app, cloud, triage, review queue, voice, popup) 사이를 더 매끄럽게 이어야 함

그래서 `Phase 7`의 본질은 `더 많은 매크로`가 아니라 `더 적은 우회와 더 좋은 네이티브 통합`입니다.

## 이 단계의 기본 철학

### 1. native가 있으면 native를 먼저 쓴다

- App Server나 공식 trigger가 가능하면 그 경로를 우선
- desktop macro는 마지막 보조 수단

### 2. deep integration은 capability detection에서 시작한다

- "무조건 App Server로 간다"가 아니라
- "지금 이 환경에서 무엇이 실제로 가능한가"를 먼저 판단

### 3. always-on은 무한 자율주행이 아니라 bounded supervision이다

- 계속 켜져 있더라도
- 언제 멈추고
- 언제 재진입하고
- 언제 ask_user로 올릴지

경계가 분명해야 합니다.

### 4. fallback은 숨기지 말고 드러내야 한다

- 지금 native 경로인지
- fallback 경로인지
- 왜 fallback으로 내려왔는지

를 상단장님이 알 수 있어야 합니다.

### 5. vendor maturity를 존중한다

- 공식 표면이 성숙하지 않으면 억지로 깊게 묶지 않음
- Phase 7은 "연구 + 얇은 연결 + 안전한 확장"이어야 함

## 이 단계에서 javis가 맡는 것

### 1. Deep Integration Capability Registry

- App Server 사용 가능 여부
- cloud trigger / background follow-up 가능 여부
- Codex app / cloud / project automation / thread automation 상태
- 현재 프로젝트에 가장 적합한 deep integration mode 추천

### 2. Integration Mode Broker

- no deep integration
- app-assisted integration
- app server integration
- cloud-trigger assisted supervision
- desktop fallback

중 어떤 경로로 운영할지 고르는 브로커

### 3. Cross-Surface Handoff Bundle

- popup에서 보던 상태
- Control Center 설정
- triage / review queue 재진입 정보
- voice briefing 요약

을 하나의 handoff 묶음으로 정리

### 4. Supervisor State Machine

- sleep
- watch
- waiting
- re-enter
- escalate
- fallback

상태를 명시적으로 갖는 상위 감독기

### 5. Fallback Boundary Manager

- native 경로가 충분하면 desktop 제어를 막음
- native 경로가 막히면 필요한 범위만 fallback 허용
- fallback 진입과 종료를 로그/상태로 남김

### 6. Integration Observability

- 현재 integration mode
- last successful handoff
- last failed handoff
- fallback reason
- re-entry source

같은 운영 정보를 한눈에 보여줌

## 이 단계에서 javis가 직접 하지 않을 것

- Codex 자체 실행 엔진 대체
- 비공식 reverse engineering에 깊게 의존하는 고정 설계
- 검수 없는 무제한 항상-실행 자율화
- native 경로가 있는데 desktop macro를 기본 경로로 쓰기

## 이 단계에서 Codex가 맡는 것

- 실제 코드 수정 / 실행 / worktree 운영
- thread / project automation
- review queue / triage / cloud follow-up
- 공식 제공 surface 위의 실행

## 이 단계에서 OpenAI 판단 계층이 맡는 것

- 현재 integration mode 추천
- re-entry 시점 판단
- fallback 진입/해제 판단
- 상단장님께 보여줄 통합 보고 문구 생성

## 대표 사용 시나리오

### 시나리오 A. App Server 사용 가능

- `javis`가 capability registry에서 App Server readiness를 확인
- 현재 프로젝트를 App Server 경유 handoff 대상으로 선택
- popup에는 `native deep integration` 상태만 보여줌

### 시나리오 B. cloud follow-up 성숙

- Codex 쪽 cloud trigger가 충분히 안정적임
- `javis`는 직접 polling보다 `watch + re-entry` 역할에 집중

### 시나리오 C. native 경로 불충분

- App Server 없음
- cloud trigger 불안정
- app surface만 사용 가능

이 경우 `javis`는 no automation / thread / project 흐름을 유지하고, 정말 필요할 때만 desktop fallback을 권함

### 시나리오 D. 여러 표면에서 다시 이어가기

- 상단장님은 popup에서 현재 상태를 보고
- Control Center에서 상세 설정을 보고
- Codex triage 결과를 다시 받아
- 같은 프로젝트 흐름으로 재진입

## 완료 조건

- 현재 환경의 deep integration capability를 감지하고 추천할 수 있음
- App Server / cloud-trigger / native app / desktop fallback 경계가 명시됨
- cross-surface handoff bundle이 존재함
- supervisor state machine이 `sleep / watch / re-enter / escalate`를 표현함
- deep integration이 `Codex-first` 원칙을 깨지 않음

## 다음 연결 문서

- `../releases/release-7-deep-integration-beta.md`
- `../specs/deep-integration-capability-matrix-v1.md`
- `../phases/phase-6-voice-assistant.md`
