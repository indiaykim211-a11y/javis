# Release 4: Judgment Beta

## 릴리즈 미션

`javis`를 `Codex 결과를 해석하고 다음 행동을 안전하게 결정하는 운영 어시스턴트`로 끌어올립니다.

이 릴리즈의 본질은 아래입니다.

- Codex 실행을 새로 만드는 것이 아니라
- Codex 결과를 `구조화 판단`으로 바꿔
- 제품 안에서 `continue / wait / retry / pause / ask_user`로 연결하는 것

## 이 릴리즈가 해결해야 하는 문제

Release 3까지 끝나면 `javis`는 Codex 앱을 아주 잘 쓰게 도와줄 수 있습니다.

하지만 아직 아래는 약합니다.

- Codex 결과를 보고 다음 행동을 자동으로 분기하는 능력
- 같은 결과라도 확신과 위험도를 같이 해석하는 능력
- 상단장님에게 왜 멈췄는지 짧게 설명하는 능력
- retry와 ask_user를 안전하게 구분하는 능력

Release 4는 이 문제를 해결하기 위해 `judgment input + structured response + decision UX + safe routing`을 제품 안으로 끌어옵니다.

## 핵심 사용자 시나리오

1. 상단장님이 현재 프로젝트를 불러옵니다.
2. Codex는 같은 스레드 또는 automation 결과를 남깁니다.
3. `javis`는 현재 프로젝트, 운영 모드, 정책, 결과 요약을 묶어 판단 요청을 만듭니다.
4. OpenAI 판단 엔진은 `continue / wait / retry / pause / ask_user` 중 하나를 반환합니다.
5. 앱은 그 결과를 팝업과 Control Center에 보여줍니다.
6. 허용되는 행동만 로컬 런타임이 실제로 이어갑니다.

## Release 4의 제품 목표

### 1) Judgment Input Foundation

- 현재 상태를 구조화된 입력으로 만들 수 있어야 합니다.
- 같은 프로젝트라도 `no automation / thread / project` 문맥 차이를 반영해야 합니다.

### 2) Structured Decision Loop

- 판단 응답은 JSON 계약 기반이어야 합니다.
- 잘못된 응답은 그대로 믿지 않고 pause 쪽으로 강등해야 합니다.

### 3) Decision UX

- 팝업과 Control Center에서 판단 결과를 바로 이해할 수 있어야 합니다.
- `왜 이런 결정을 했는지`가 짧게 보여야 합니다.

### 4) Safe Action Routing

- continue / retry / pause / ask_user가 실제 후속 흐름으로 연결돼야 합니다.
- high risk, low confidence는 공격적으로 집행되면 안 됩니다.

## 포함 범위

- judgment packet builder
- judgment prompt assembly
- structured response validator
- popup / control center decision surface
- decision action router
- judgment timeline / evidence digest
- confidence / risk guard

## 제외 범위

- OCR / 비전 판독
- 브라우저 화면 실제 이해
- 음성 입출력
- App Server 직접 연동
- Codex 실행 엔진 재구현

## 필수 기능 기준

### judgment input

- 현재 프로젝트 / 현재 단계 / 운영 모드 / 정책 / 최근 결과를 구조화해 넣을 수 있어야 함

### structured response

- 허용된 decision set만 통과
- confidence / risk / user message 필수

### decision surface

- popup에서 핵심 판단이 보임
- Control Center에서 근거와 follow-up이 보임

### safe routing

- retry는 재지시 문구와 이어짐
- ask_user는 상단장님 확인 요청으로 이어짐
- high risk는 자동 continue 불가

## 성공 기준

### 사용자 경험 기준

- 상단장님이 `왜 계속 가는지 / 왜 멈췄는지` 바로 이해할 수 있음
- Codex 결과가 올라왔을 때 다음 행동이 명확함
- 애매한 상황에서 과감하게 진행하지 않음

### 제품 기준

- `javis`가 단순 orchestration 툴에서 `판단형 감독자`로 올라감
- Release 5에서 화면 인식 근거를 쉽게 붙일 수 있음
- Phase 3 운영 흐름과 충돌하지 않고 자연스럽게 얹힘

## 주요 산출물

- Judgment Packet Builder v1
- Structured Decision Loop v1
- Decision Surface v1
- Safe Routing v1

## 주요 리스크

### 1) 모델 자유서술이 다시 새어 나올 수 있음

- 해결 방향: 응답 계약 강제 + validator에서 강등

### 2) 판단은 생겼는데 실제 후속 흐름이 약할 수 있음

- 해결 방향: continue / retry / ask_user를 제품 행동과 직접 연결

### 3) 확신 낮은 continue가 위험할 수 있음

- 해결 방향: confidence / risk guard를 별도 계층으로 둠

## Release 4 완료 선언 조건

1. 현재 프로젝트와 최근 Codex 결과를 구조화된 judgment input으로 만들 수 있음
2. 구조화 응답을 검증하고 안전하게 분기할 수 있음
3. 팝업과 Control Center에서 판단 결과가 짧고 명확하게 보임
4. 상단장님 기준으로 `이제 javis가 단순 도우미가 아니라 판단하는 감독자처럼 느껴짐`
