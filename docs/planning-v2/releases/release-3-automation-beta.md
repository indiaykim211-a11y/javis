# Release 3: Automation Beta

## 릴리즈 미션

`javis`를 `Codex 앱을 아주 잘 쓰는 오케스트레이터`로 끌어올립니다.

이 릴리즈의 본질은 자체 자동화 엔진을 키우는 것이 아니라, `Codex Automations를 제품 안에서 자연스럽게 선택, 준비, launch, 재진입`하게 만드는 것입니다.

## 이 릴리즈가 해결해야 하는 문제

현재 상태의 가장 큰 문제는 아래입니다.

- 어떤 상황에 automation이 필요한지 아직 상단장님이 매번 직접 판단해야 함
- thread automation과 project automation의 차이가 문서엔 있지만 제품 흐름으로는 아직 약함
- prompt는 만들 수 있어도 `그 다음에 뭘 해야 하는지`가 완전한 launch flow로 이어지진 않음
- 결과를 다시 어디서 봐야 하는지, 언제 멈춰야 하는지 운영 기준이 더 필요함

Release 3는 이 문제를 해결하기 위해 `automation mode decision + launch flow + operations surface`를 제품 안으로 끌어옵니다.

## 핵심 사용자 시나리오

1. 상단장님이 현재 프로젝트를 불러옵니다.
2. `javis`는 먼저 `automation 없이 같은 스레드로 갈지`, `thread automation을 쓸지`, `project automation을 쓸지` 추천합니다.
3. 상단장님은 추천 전략을 선택합니다.
4. 앱은 prompt, handoff, cadence, worktree 메모를 한 번에 보여줍니다.
5. 상단장님은 Codex 앱에서 automation을 만들거나, 그대로 같은 스레드 순차 진행으로 운영합니다.
6. 결과가 다시 올라오면 `javis`는 어디를 봐야 하는지와 다음 행동을 요약합니다.

## Release 3의 제품 목표

### 1) Automation mode decision

- 자동화가 필요한지부터 먼저 판단하게 해야 합니다.
- 무조건 automation으로 몰아가지 않아야 합니다.

### 2) Launch-ready handoff

- 선택한 전략을 Codex에 바로 옮길 수 있어야 합니다.
- prompt, cadence, worktree, safety 메모가 함께 묶여야 합니다.

### 3) Operations surface

- 지금 무엇이 실행 중인지
- 무엇을 기다리는지
- 결과는 어디서 다시 봐야 하는지

를 제품 안에서 이해할 수 있어야 합니다.

## 포함 범위

- automation mode selector
- thread automation composer
- project automation composer
- launch checklist / handoff
- automation runboard
- triage summary bridge
- automation safety guard

## 제외 범위

- 자체 스케줄러 구축
- 자체 background task 실행기 구축
- App Server 직접 연동
- 화면 인식 / OCR
- 음성 입출력

## 필수 기능 기준

### automation mode selector

- no automation / thread / project 중 추천 가능
- 추천 이유가 짧게 보여야 함

### automation composer

- 현재 프로젝트 기준 prompt 초안
- cadence 제안
- worktree 메모
- handoff 복사 흐름

### operations surface

- 최근 선택한 automation 전략 표시
- 결과 확인 위치 안내
- 다음 follow-up 액션 안내

## 성공 기준

### 사용자 경험 기준

- 상단장님이 `지금 automation이 필요한지` 바로 이해할 수 있음
- Codex 앱으로 옮겨 가는 흐름이 자연스러움
- Codex 결과를 다시 볼 자리와 타이밍이 명확함

### 제품 기준

- `javis`가 Codex app의 automation 기능을 잘 쓰게 만드는 제품이 됨
- no automation / thread / project 구분이 제품에 녹아 있음
- Release 4 판단 엔진과도 자연스럽게 이어질 수 있음

## 주요 산출물

- Automation Mode Selector v1
- Thread / Project Automation Composer v1
- Automation Launch Flow v1
- Automation Runboard v1

## 주요 리스크

### 1) automation을 너무 쉽게 권해 과도하게 복잡해질 수 있음

- 해결 방향: `no automation`을 정식 선택지로 둠

### 2) Codex 앱의 실제 결과 확인 동선이 아직 제품에 약할 수 있음

- 해결 방향: Triage / 스레드 재진입 가이드를 UI에 명시

### 3) launch flow가 문서 복붙 수준에 머물 수 있음

- 해결 방향: handoff 패널과 runboard를 실제 제품 플로우로 연결

## Release 3 완료 선언 조건

1. 현재 프로젝트에 맞는 automation mode를 고를 수 있음
2. Codex 앱에서 바로 쓸 수 있는 launch-ready prompt/handoff를 만들 수 있음
3. 결과를 다시 확인하고 다음 행동으로 이어지는 운영 흐름이 제품에 있음
4. 상단장님 기준으로 `Codex 앱을 정말 잘 쓰는 javis`라는 느낌이 듦
