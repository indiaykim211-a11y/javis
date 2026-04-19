# Phase 3: Automation Orchestrator

## 단계 목적

이 단계의 목적은 `javis`가 Codex Automations를 대신 구현하는 앱이 아니라, `Codex 앱의 automation 기능을 가장 잘 쓰게 해 주는 운영 오케스트레이터`가 되는 것입니다.

핵심 질문은 아래 3개입니다.

1. 지금 이 작업은 `자동화 없이 같은 스레드에서 순차 진행`하면 되는가
2. `thread automation`으로 다시 깨우는 것이 맞는가
3. `standalone / project automation`으로 분리하는 것이 맞는가

## 왜 이 단계가 필요한가

Phase 2에서 우리는 `Codex-first` 방향을 정리하고,

- 어떤 전략을 쓸지 고를 수 있게 했고
- 프로젝트 기준 prompt 초안을 만들 수 있게 했고
- runbook과 native/fallback 원칙을 보이게 했습니다.

이제 Phase 3에서는 한 단계 더 나아가,

- 어떤 automation 방식을 선택할지
- 어떻게 launch할지
- 결과를 어디서 다시 볼지
- 언제 계속하고 언제 멈출지

를 제품 차원에서 다뤄야 합니다.

## 이 단계의 기본 철학

### 1. 자동화는 항상 필요한 것이 아니다

가장 먼저 해야 할 판단은 `automation을 쓸까 말까` 입니다.

아래 상황이면 automation 없이 같은 스레드에서 순차 진행이 더 좋습니다.

- 마스터플랜이 이미 잘 짜여 있음
- 외부 대기 시간이 거의 없음
- 단계가 자연스럽게 바로 이어짐
- 굳이 주기적으로 다시 깨울 필요가 없음

즉 Phase 3의 첫 기능은 `automation 생성기`보다 `automation 필요 여부 판단기`에 가깝습니다.

### 2. thread automation은 문맥 유지용이다

thread automation은 `같은 대화 맥락을 다시 깨울 때` 씁니다.

- 같은 운영 스레드를 유지하고 싶을 때
- follow-up, babysitting, periodic check가 필요할 때
- 단계 완료 즉시 이벤트보다 `몇 분 / 몇 시간 뒤 다시 보기`가 더 자연스러울 때

### 3. project automation은 독립 실행용이다

standalone / project automation은 `매 실행을 따로 보고 싶을 때` 맞습니다.

- nightly brief
- release smoke
- CI triage
- 독립적인 반복 점검

### 4. javis의 역할은 launch와 supervision이다

이 단계에서도 `javis`는 직접 스케줄러를 새로 만들지 않습니다.

대신 아래를 잘해야 합니다.

- 자동화 방식 추천
- prompt와 handoff 준비
- worktree 권장
- 결과 재진입 동선 정리
- stop / pause / ask_user 기준 유지

## 이 단계에서 javis가 직접 하지 않을 것

- 자체 반복 실행 엔진을 새로 만들기
- 자체 cron 시스템 만들기
- 자체 background task 관리자 만들기
- Codex가 이미 하는 scheduling을 다시 구현하기
- Codex 앱을 계속 눌러 automation을 흉내 내기

## 이 단계에서 javis가 맡을 것

### 1. Automation mode decision

- no automation
- thread automation
- standalone / project automation

중 무엇이 맞는지 먼저 제안합니다.

### 2. Automation authoring assistant

- 선택한 방식에 맞는 prompt 조합
- cadence 힌트
- worktree 권장
- handoff 문구

를 제품 안에서 묶어 줍니다.

### 3. Automation operations surface

- 지금 어떤 automation이 왜 추천됐는지
- 최근 어떤 전략을 썼는지
- 다음에 어디를 봐야 하는지
- Triage / 결과 확인은 어떻게 할지

를 짧게 정리합니다.

### 4. Safety overlay

- 자동화가 과한 상황에서는 no automation을 추천
- 반복 실패 시 stop / ask_user 권장
- native 우선, fallback 보조 원칙 유지

## 이 단계에서 Codex가 맡는 것

- thread automation 실행
- project automation 실행
- worktree 기반 반복 작업
- Triage / 결과 큐 제공
- scheduled follow-up

## 이 단계에서 OpenAI 판단 엔진이 맡는 것

- 어떤 automation 방식이 맞는지 설명
- 계속 / 보류 / ask_user 판단 보조
- 결과를 운영자 친화적으로 요약
- 재지시 또는 후속작업 문구 생성

## 이 단계의 핵심 사용자 시나리오

### 시나리오 A. 같은 스레드 순차 진행이 더 나은 경우

- 상단장님이 마스터플랜을 확정함
- Codex가 같은 스레드에서 순차 진행
- `javis`는 automation 없이도 충분하다고 안내

### 시나리오 B. thread automation follow-up

- 같은 운영 스레드를 유지해야 함
- Codex가 몇 분 간격으로 다시 와서 상태를 봐야 함
- `javis`는 heartbeat 프롬프트와 운영 규칙을 준비

### 시나리오 C. project automation smoke / brief

- release smoke나 nightly brief처럼 독립 실행이 좋음
- `javis`는 worktree, cadence, prompt를 제안

### 시나리오 D. Triage 기반 재진입

- 결과는 Codex 쪽에서 올라옴
- `javis`는 상단장님이 무엇을 다시 열어봐야 하는지 요약

## 완료 조건

- `automation을 쓸지 말지`부터 제품 안에서 판단할 수 있음
- thread / project automation 차이를 상단장님이 바로 이해할 수 있음
- automation prompt / handoff / launch 흐름이 제품에 들어옴
- Codex 결과를 다시 확인하는 운영 동선이 정리됨
- `Codex 앱을 아주 잘 쓰는 javis`라는 느낌이 분명해짐

## 다음 연결 문서

- `../releases/release-3-automation-beta.md`
- `../codex/codex-automations-playbook-v1.md`
- `../codex/javis-codex-automation-scenarios-v1.md`
- `../codex/automation-prompt-templates-v1.md`
