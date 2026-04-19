# Release 7: Deep Integration Beta

## 릴리즈 미션

`Release 7`의 목표는 `javis`를 "매크로가 많은 도구"가 아니라 `Codex 네이티브 표면을 가장 잘 쓰는 상위 감독기`로 한 단계 더 올리는 것입니다.

## 이번 릴리즈가 해결해야 하는 문제

지금까지는:

- popup / Control Center 운영 표면
- Codex strategy / automation 선택
- judgment / visual / voice 감독

까지 갖췄습니다.

다음 문제는 보통 이렇게 나타납니다.

- 어떤 프로젝트는 thread automation이면 충분함
- 어떤 프로젝트는 project automation이 더 맞음
- 어떤 환경은 App Server나 더 직접적인 연결을 고려할 수 있음
- 어떤 상황은 native로 충분한데 desktop fallback이 섞이면 오히려 복잡해짐

즉 `무엇을 할 수 있나`보다 `무엇을 어떻게 연결해야 하나`가 더 중요한 단계입니다.

## 제품 목표

### 1) Capability Discovery

- 현재 환경에서 사용 가능한 deep integration 표면 감지
- App Server / cloud trigger / app-native / desktop fallback 경계 정리

### 2) Integration Mode Broker

- 현재 프로젝트와 운영 상태에 맞는 integration mode 추천
- native 우선, fallback 최소화

### 3) Cross-Surface Handoff

- popup / Control Center / Codex triage / review queue / voice 사이의 재진입 흐름 정리

### 4) Supervisor Layer

- watch / wait / re-enter / escalate / fallback 상태를 명시적 모델로 표현

### 5) Fallback Governance

- desktop fallback 진입 이유와 종료 이유를 명확히 기록
- native가 충분할 때는 fallback을 막음

## 포함 범위

- capability registry
- integration mode selector
- App Server adapter skeleton
- cloud trigger readiness tracker
- cross-surface handoff bundle
- supervisor state model
- fallback boundary manager
- release 7 smoke suite 문서 기준

## 제외 범위

- Codex core execution 대체
- 비공식 reverse engineering 중심의 깊은 종속
- 항상-실행 완전 자율 배포
- native가 있는데도 desktop control을 기본 경로로 강제

## 핵심 기능 기준

### capability registry

- 현재 환경에서 가능한 연결 방식을 구조화 정보로 보여줄 수 있어야 함

### mode broker

- 추천 경로와 실제 선택 경로를 구분해 보여줘야 함

### handoff bundle

- 재진입에 필요한 프로젝트/상태/리스크 정보를 한 번에 넘길 수 있어야 함

### supervisor

- 지금 sleep인지, watch인지, waiting인지, escalate인지 보여줄 수 있어야 함

### fallback governance

- fallback은 허용/차단/종료 기준이 분명해야 함

## 성공 기준

### 사용자 경험 기준

- 상단장님이 "지금 javis가 어떤 연결 모드로 운영 중인지" 이해할 수 있음
- native 경로가 충분한데 왜 fallback을 안 쓰는지 설명할 수 있음
- native 경로가 막혔을 때 왜 fallback으로 내려왔는지 설명할 수 있음

### 제품 기준

- integration mode 추천과 handoff 정보가 일관됨
- supervisor state가 popup / Control Center / voice 보고에서 같은 뜻을 가짐
- desktop fallback이 기본 전략이 아니라 예외 경로로 유지됨

## 주요 리스크

### 1) 공식 표면 성숙도가 아직 애매할 수 있음

- 해결 방향: hard dependency 대신 readiness tracker와 adapter skeleton으로 설계

### 2) deep integration이 제품을 과도하게 복잡하게 만들 수 있음

- 해결 방향: capability registry와 mode broker를 중심으로 단순화

### 3) fallback 경계가 흐려질 수 있음

- 해결 방향: fallback boundary 문서와 runtime observability를 함께 설계

## 주요 산출물

- Deep Integration Capability Matrix v1
- Integration Mode Broker v1
- App Server Adapter Skeleton v1
- Cross-Surface Handoff Bundle v1
- Supervisor State Model v1
- Release 7 Smoke Checklist v1

## 완료 선언 조건

1. 현재 환경의 deep integration capability를 구조화해서 보여줄 수 있음
2. integration mode 추천과 override 기준이 정리됨
3. cross-surface handoff bundle이 정의됨
4. fallback boundary가 문서와 제품 흐름 모두에서 설명 가능함
