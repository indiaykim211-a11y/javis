# javis 마스터플랜 v2

## 0. 문서 목적

이 문서는 `javis`를 다시 정의한 상위 개발계획의 큰 얼개입니다.

- 이번 버전은 `상세 구현서`가 아니라 `방향 정렬용 마스터 아웃라인`입니다.
- 기존 상세본은 `docs/archive/javis-master-plan-v1-operator-console.md`에 보존합니다.
- 이후 단계에서는 이 문서를 기준으로 릴리즈, 에픽, 스프린트, 티켓으로 다시 살을 붙입니다.

## 1. 방향 전환 선언

`javis`의 본질은 `Codex를 대체하는 새 개발 엔진`이 아니라, `Codex를 최대한 활용하는 상위 데스크톱 어시스턴트`입니다.

핵심 전환은 아래와 같습니다.

- 메인 사용자 경험은 `작은 어시스턴트 팝업`이어야 합니다.
- 설정, 로그, 캘리브레이션, 프롬프트 편집은 `별도 설정/운영 창`으로 숨깁니다.
- `창 제어 툴`이 아니라 `Codex 개발 진행을 끝까지 관리하는 판단형 어시스턴트`로 설계합니다.
- `Codex app / cloud / worktrees / review queue / automations / skills` 같은 네이티브 기능을 먼저 씁니다.
- 데스크톱 클릭 자동화와 화면 매크로는 `1차 선택지`가 아니라 `빈틈을 메우는 보조 수단`으로 둡니다.

## 2. 제품 한 줄 정의

`javis는 Codex의 네이티브 작업 능력과 Automations를 최대한 활용하면서, 장기 개발 플랜을 감독하고 판단하고 이어붙여 주는 한국어 중심 데스크톱 어시스턴트입니다.`

## 3. 최종 제품 형태

### 3-1. 사용자에게 보이는 메인 화면

항상 떠 있을 수 있는 작은 어시스턴트 팝업입니다.

- 현재 상태 한 줄 요약
- 지금 무엇을 하고 있는지
- 왜 멈췄는지 또는 왜 다음으로 가는지
- `진행`, `보류`, `멈춤`, `요약`, `말하기` 같은 짧은 액션
- 나중에는 음성 입력과 음성 응답

### 3-2. 보조 화면

설정/운영용 컨트롤 센터입니다.

- OpenAI 프롬프트 정책
- Codex 타겟 설정
- 스크린샷/로그/증거 보기
- 안전 규칙
- 모델/음성/자동화 옵션

### 3-3. 핵심 UX 원칙

- 상단장님은 `어시스턴트`와 대화해야지 `운영 패널`을 계속 조작하면 안 됩니다.
- 복잡한 것은 숨기고, 중요한 판단만 짧게 보여줘야 합니다.
- 확신이 낮으면 자동 진행보다 `보류 + 설명`이 우선입니다.

## 4. 우선순위 재정의

상단장님 기준 우선순위는 아래 3개입니다.

### 4-1. 1순위: Codex 개발 진행 제어

가장 먼저 완성해야 하는 것은 `Codex가 마스터 개발 플랜 끝까지 달리게 만드는 능력`입니다.

- 단계 포인터 관리
- 다음 단계 전송
- 진행 상태 모니터링
- 보류/재시도/수정 요청
- 장시간 실행 안정성

### 4-2. 2순위: 화면 인식

`읽을 수 있어야` 제대로 판단할 수 있습니다.

- Codex 화면 읽기
- 브라우저 결과 화면 읽기
- 오류, 정지, 불완전 상태 감지
- 결과물 품질에 대한 기초 판단

### 4-3. 3순위: 음성

음성은 중요한 완성형 경험이지만, 앞의 두 능력이 먼저 단단해야 합니다.

- 음성 입력
- 음성 응답
- 나중에는 웨이크워드

## 5. OpenAI와 Codex의 역할

피디 판단으로 `OpenAI 모델은 초반부터 중요하지만, 먼저 최대한 활용해야 하는 것은 Codex가 이미 가진 네이티브 기능`입니다.

이유는 간단합니다.

- Codex는 이미 `클라우드 작업`, `병렬 작업`, `worktrees`, `review queue`, `automations`, `skills`를 제공합니다.
- 이 부분을 새로 만드는 것보다, 그 위에서 `감독과 통합`을 붙이는 편이 빠르고 안전합니다.
- 그래도 “지금 멈춘 게 정상인지”, “다음 단계로 가도 되는지”, “이상 신호가 있는지”는 모델 판단이 계속 필요합니다.

단, 역할 분리는 명확해야 합니다.

- Codex 네이티브 레이어: 실제 코드 작업, 클라우드 태스크, worktree 분리, review queue, scheduled automations
- javis 오케스트레이션 레이어: 마스터플랜 로드, 정책 적용, 상태 통합, 사용자 보고, Codex 재지시 흐름 정리
- 데스크톱 로컬 레이어: 화면 캡처, 브라우저/앱 상태 읽기, 팝업 UI, 필요한 경우에만 클릭 자동화
- OpenAI 판단 레이어: 상황 판단, 다음 행동 결정, 사용자 보고 문구 생성, Codex 재지시 문구 생성

즉 초기 전략은 `실행은 Codex`, `감독은 javis`, `판단은 OpenAI`, `로컬 제어는 보조` 구조가 기본입니다.

## 6. 프롬프트 전략 원칙

긴 프롬프트 하나로 모든 상황을 처리하기보다, `정책 모듈`로 나누는 것이 맞습니다.

### 6-1. 필요한 프롬프트 계층

- 운영 마스터 프롬프트
- 단계 진행 판단 프롬프트
- 화면 판독 프롬프트
- 사용자 보고 프롬프트
- 안전 규칙 프롬프트

### 6-2. 판단 출력 방식

자유서술이 아니라 구조화된 응답이 기본이어야 합니다.

예:

```json
{
  "decision": "continue | wait | retry | pause | ask_user",
  "reason": "판단 근거",
  "confidence": 0.0,
  "message_to_user": "상단장님께 보여줄 짧은 메시지",
  "next_prompt_to_codex": "필요할 때만",
  "risk_level": "low | medium | high"
}
```

## 7. 핵심 시스템 아키텍처

상위 구조는 아래 7개 레이어로 봅니다.

### 7-1. Assistant Surface

사용자에게 보이는 작은 팝업 어시스턴트입니다.

### 7-2. Control Center

설정, 로그, 디버그, 프롬프트 편집, 캘리브레이션을 담당하는 숨은 운영석입니다.

### 7-3. Codex Native Layer

Codex app / web / cloud가 이미 제공하는 핵심 실행 레이어입니다.

- cloud task 실행
- worktree 기반 병렬 작업
- review queue 기반 결과 확인
- thread / project automation
- skills 기반 확장

### 7-4. Orchestration & Policy Layer

javis가 위에서 덮는 운영 레이어입니다.

- 마스터플랜 로드
- 단계 포인터 / 큐 관리
- 정책 모듈 적용
- Codex 결과와 다음 액션 연결

### 7-5. Judgment Engine

OpenAI 기반 판단 엔진입니다.

- 현재 상태 해석
- 다음 액션 결정
- Codex용 재지시 생성
- 사용자용 보고 생성

### 7-6. Visual Context Pipeline

스크린샷, OCR/비전, 브라우저 상태, 결과 화면 의미 해석을 담당합니다.

### 7-7. Integration Layer

후반부 확장 레이어입니다.

- 음성 입력 / 음성 출력
- App Server 같은 더 직접적인 연결 방식 연구
- 데스크톱 클릭 자동화 fallback
- 더 깊은 always-on 감독

## 8. 새 로드맵 큰 얼개

### Phase 1. Assistant Shell

`javis`를 콘솔형 툴이 아니라 어시스턴트형 앱으로 보이게 만드는 단계입니다.

- 작은 팝업 UI
- 상태 요약 중심 인터랙션
- 설정/운영 창 분리
- 세션/프로젝트 불러오기

### Phase 2. Codex-First Foundation

`Codex가 이미 제공하는 기능을 운영 뼈대에 먼저 편입`하는 단계입니다.

상세 전략은 `docs/planning-v2/phases/phase-2-codex-first-foundation.md`로 이어집니다.

- Codex cloud / app 흐름 정리
- thread / project 단위 운영 구조 확정
- review queue와 결과 확인 방식 정리
- skills / rules / worktree 활용 전략 정리

### Phase 3. Automation Orchestrator

`Codex Automations를 중심으로 장기 실행을 붙이는 단계`입니다.

상세 활용 가이드는 `docs/planning-v2/phases/phase-3-automation-orchestrator.md`와
`docs/planning-v2/codex/codex-automations-playbook-v1.md`로 이어집니다.

- no automation / thread / project 판단
- thread automation 활용
- project automation 활용
- 자동 재진입 / 자동 요약 / 자동 후속작업
- 마스터플랜 기준 자동 이어가기

### Phase 4. Judgment Overlay

`Codex 결과를 위에서 해석하고 분기시키는 판단층`을 만드는 단계입니다.

- OpenAI 판단 엔진 1차 연결
- continue / pause / retry / ask-user 분기
- 정책 기반 재지시
- 사용자 보고 품질 강화

### Phase 5. Visual Supervisor

`화면을 읽고 판단 근거를 강화`하는 단계입니다.

- Codex 화면 캡처 해석
- 브라우저 결과 화면 해석
- 품질 이상 신호 감지
- 시각 증거 기반 판단

### Phase 6. Voice Assistant

`말로 쓰는 javis`로 넘어가는 단계입니다.

- push-to-talk
- 한국어 STT
- 한국어 TTS 브리핑
- 음성 명령 기반 진행/보류/요약

### Phase 7. Deep Integration

완성형에 가까운 단계입니다.

- App Server 연구 및 연결 검토
- cloud-based trigger 성숙도 반영
- 더 깊은 항상-실행 감독
- 필요한 경우에만 데스크톱 제어 fallback 유지

## 9. 릴리즈 관점 재정리

### Release 1. Assistant Alpha

작은 팝업 + 설정창 분리 + 기본 세션 복원

### Release 2. Codex-First Beta

Codex 네이티브 기능 중심 운영 뼈대 확정

### Release 3. Automation Beta

Codex Automations를 활용한 장기 작업 운영

### Release 4. Judgment Beta

OpenAI 판단 엔진이 위에서 감독하는 구조

### Release 5. Visual Beta

화면 인식과 브라우저 판독이 붙은 상태

### Release 6. Voice / Deep Integration

음성 입출력과 더 직접적인 Codex 연동 연구

## 10. 지금 당장 중요한 설계 결론

### 10-1. 메인 UX

지금부터 모든 기능은 `작은 어시스턴트 팝업에서 어떻게 보일지`를 먼저 기준으로 삼습니다.

### 10-2. Codex-first 전략

새 기능을 만들기 전에 `Codex 앱 / cloud / automations / review queue / worktrees / skills`로 되는지 먼저 확인합니다.

### 10-3. 판단 엔진

OpenAI 판단은 필요하지만 `Codex 네이티브 실행` 위에 덮는 감독층으로 설계합니다.

### 10-4. 화면 인식

화면 인식은 여전히 옵션이 아니라 사실상 필수 경로입니다.

### 10-5. 음성

음성은 `push-to-talk -> TTS -> 웨이크워드` 순서로 갑니다.

### 10-6. 로컬 데스크톱 제어

클릭 자동화와 화면 매크로는 `맨 앞 기능`이 아니라 `네이티브 연동으로 안 되는 부분을 메우는 fallback`으로 둡니다.

## 11. 다음에 살을 붙일 순서

다음 문서화/기획은 아래 순서가 좋습니다.

1. `Codex native 활용 전략` 상세화
2. `Automations 활용 시나리오` 상세화
3. `Phase 1 + Release 1` 상세화
4. `Assistant Popup UX` 상세화
5. `OpenAI 판단 스키마` 상세화
6. `Visual Intelligence 입력/출력 규격` 상세화
7. `App Server 연구 메모` 상세화

## 12. 한 줄 결론

`javis는 Codex를 다시 만드는 앱이 아니라, Codex의 네이티브 능력을 최대한 활용하면서 그 위를 감독하고 이어붙이는 데스크톱 어시스턴트로 설계되어야 합니다.`
