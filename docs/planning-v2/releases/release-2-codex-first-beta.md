# Release 2: Codex-First Beta

## 릴리즈 미션

`javis`가 `Codex를 직접 대체하려는 앱`이 아니라, `Codex 네이티브 기능을 가장 영리하게 활용하는 감독자`로 방향을 분명히 굳히는 릴리즈입니다.

## 이 릴리즈가 해결해야 하는 문제

현재 상태의 가장 큰 문제는 아래입니다.

- 앱 구조는 좋아졌지만, 아직 `Codex를 어떻게 네이티브하게 운영할지`가 제품 안에서 잘 안 보임
- 상단장님이 `thread automation`, `project automation`, `worktree`, `nightly brief` 같은 운영 선택을 앱 안에서 바로 판단하기 어려움
- 문서로는 방향이 정리됐지만, 실제 앱 안에서는 아직 `Codex-first 운영 가이드`가 표면화되지 않음

Release 2는 이 문제를 해결하기 위해 `Codex 전략을 제품 안에서 바로 선택하고 준비하게 하는 기반`을 만듭니다.

## 핵심 사용자 시나리오

1. 상단장님이 `마스터플랜이 준비된 프로젝트`를 불러옵니다.
2. `javis`는 현재 프로젝트에 맞는 Codex 운영 시나리오를 보여줍니다.
3. 상단장님은 `follow-up heartbeat`, `release smoke`, `nightly brief` 같은 전략 중 하나를 고릅니다.
4. 앱은 추천 automation 유형, worktree 권장 여부, 프롬프트 초안을 즉시 보여줍니다.
5. 상단장님은 그 초안을 Codex에 바로 옮기거나, 다음 Release에서 자동화 생성으로 이어갈 수 있습니다.

## Release 2의 제품 목표

### 1) Codex-first 전략의 제품화

- 문서에만 있는 전략이 아니라, 앱 안에서 바로 선택 가능한 구조여야 합니다.
- `무엇을 Codex에 맡기고 무엇을 javis가 감독할지`가 분명히 보여야 합니다.

### 2) 운영 프리셋 도입

- 자주 쓸 Codex 운영 패턴을 `시나리오 프리셋`으로 제공해야 합니다.
- 상단장님이 매번 처음부터 장문 지시를 다시 쓰지 않아도 돼야 합니다.

### 3) Release 3 자동화로 가는 발판

- Release 2는 아직 `실제 자동화 생성기 완성`이 아니라, 그 전에 필요한 전략/프로필/런북 기반을 갖추는 단계입니다.
- 이후 Release 3에서 Codex Automations를 더 직접적으로 다룰 수 있게 준비돼야 합니다.

## 포함 범위

- Codex 전략 센터
- 시나리오 프리셋 라이브러리
- 프로젝트 기준 automation prompt 초안 생성
- 프로젝트별 Codex 운영 프로필 기초 저장
- worktree / native / fallback 설명 패널
- Release 3로 이어질 런북 진입점

## 제외 범위

- Codex automation 생성 완전 자동화
- OpenAI 판단 엔진 본격 연결
- 화면 인식 / OCR
- 음성 입출력
- App Server 직접 연동

## 필수 기능 기준

### Codex 전략 센터

- 추천 시나리오 선택 가능
- 추천 automation 유형 표시
- cadence / worktree / 위험 메모 표시
- 프로젝트 기준 프롬프트 초안 미리보기
- 클립보드 복사 또는 후속 흐름 진입

### 프로젝트 프로필

- 현재 프로젝트가 어떤 Codex 운영 전략을 쓰는지 저장 가능
- 최근 프로젝트를 다시 불러왔을 때 전략 선택도 이어짐

### 운영 가이드

- 언제 `thread automation`을 쓰는지 보임
- 언제 `project automation`을 쓰는지 보임
- 언제 `로컬 데스크톱 제어 fallback`이 필요한지 보임

## 성공 기준

### 사용자 경험 기준

- 상단장님이 `이 프로젝트는 어떤 Codex 운영 모드가 맞는지` 앱 안에서 바로 이해할 수 있음
- Codex에 붙일 초안 프롬프트를 빠르게 만들 수 있음
- `문서만 읽고 판단해야 하는 부담`이 줄어듦

### 제품 기준

- Release 2가 끝나면 `Codex-first 전략`이 제품 안에서 실제 표면으로 올라와 있음
- Release 3에서 Automations 기능을 붙일 자리가 정리돼 있음
- 기존 Release 1의 팝업/Control Center 구조와 자연스럽게 이어짐

## 주요 산출물

- Codex Strategy Center v1
- Scenario Preset Library v1
- Project Operating Profile v1
- Release 3 Automation Runbook Entry

## 주요 리스크

### 1) 전략 문서가 앱에 들어왔지만 여전히 추상적으로 느껴질 수 있음

- 해결 방향: 프리셋, 추천 유형, 실제 프롬프트 초안까지 한 화면에서 연결

### 2) 너무 많은 시나리오가 한꺼번에 나오면 다시 복잡해질 수 있음

- 해결 방향: 상단장님 우선순위 기준 상위 시나리오부터 먼저 노출

### 3) 네이티브 전략과 기존 로컬 제어가 섞여 혼란을 줄 수 있음

- 해결 방향: `네이티브 우선, 로컬 fallback` 원칙을 UI 문구와 런북에서 반복 고정

## Release 2 완료 선언 조건

1. 프로젝트마다 적절한 Codex 운영 시나리오를 고를 수 있음
2. 현재 프로젝트 기준으로 Codex용 prompt 초안을 빠르게 만들 수 있음
3. 상단장님이 `이건 Codex-first 앱이다`라고 체감할 수 있음
4. Release 3의 실제 Automations 구현으로 자연스럽게 넘어갈 수 있음
