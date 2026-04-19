# Phase 8: Live Operations

## 단계 목표

`Phase 8`은 `javis`를 "기능이 많은 조정기"에서 `실제로 Codex 운영을 굴리는 상위 오퍼레이터`로 올리는 단계입니다.

핵심은 3가지입니다.

- 지금 어떤 운영 레인에 있는지 분명히 보이게 하기
- Codex 결과가 돌아왔을 때 어디로 어떻게 재진입할지 정해두기
- 막혔을 때 복구 플레이북을 바로 꺼내 쓸 수 있게 하기

## 왜 이 단계가 필요한가

`Phase 7`까지 오면:

- Codex-first 전략
- Deep Integration 경계
- judgment / visual / voice 감독

까지는 갖춰집니다.

그 다음 병목은 보통 `실전 운영 흐름`에서 생깁니다.

- 지금 바로 launch해야 하는지
- 그냥 기다리면 되는지
- 결과가 돌아왔으니 다시 같은 스레드로 들어가야 하는지
- triage를 먼저 읽어야 하는지
- 막혔을 때 수동 게이트로 바꿔야 하는지

이걸 사람이 매번 즉흥적으로 판단하면 운영이 다시 무거워집니다.

## 기본 원칙

### 1. 운영은 lane으로 본다

- launch_ready
- active_run
- waiting_result
- reentry_ready
- blocked
- manual_review

지금 어디에 있는지 먼저 보여주고, 그 lane에 맞는 다음 행동을 제시합니다.

### 2. Codex native 흐름을 계속 우선한다

- same-thread
- triage-first
- manual-gate

중 어떤 재진입 방식이 맞는지 먼저 고르고, 그 다음에만 추가 개입을 합니다.

### 3. recovery는 자동보다 설명 가능해야 한다

- 왜 막혔는지
- 어느 수준으로 복구해야 하는지
- 누가 다음 결정을 내려야 하는지

를 항상 짧게 설명할 수 있어야 합니다.

## 이 단계에서 javis가 맡는 것

### 1. Live Ops Profile

- hands-off / balanced / guarded
- report cadence
- re-entry preference
- unattended step 한도

### 2. Live Ops Lane Model

- 현재 lane 추천
- lane 이유
- 다음 operator touchpoint
- recovery level

### 3. Operations Charter

- Codex에 맡길 때 유지할 운영 규칙
- bounded supervision 원칙
- 보고 cadence
- 재진입 규칙

### 4. Launchpad

- 지금 launch 가능한지
- 어떤 launch mode인지
- immediate action이 뭔지

### 5. Re-entry Brief

- 결과를 어디서 먼저 읽을지
- 읽고 나서 어떤 순서로 이어갈지
- watch해야 할 위험 신호가 뭔지

### 6. Recovery Playbook

- blocked / manual review / retry 상황별 복구 지침

### 7. Shift Brief

- 운영자 시점의 짧은 현재 상태 요약

## 이 단계에서 Codex가 맡는 것

- 실제 코드 작성과 수정
- thread / project automation 실행
- triage / review queue / follow-up 결과 생성

## 완료 기준

1. 운영 프로필이 세션과 프로젝트 단위로 저장/복원된다.
2. 현재 lane과 touchpoint가 Control Center에서 바로 보인다.
3. operations charter / launchpad / re-entry brief / recovery playbook / shift brief가 모두 생성된다.
4. project home에서도 현재 live ops 상태를 요약해서 볼 수 있다.
5. release 8 smoke로 기본 운영 흐름을 반복 점검할 수 있다.
