# Release 6: Voice Beta

## 릴리즈 미션

`javis`를 `작은 데스크톱 assistant + Codex-first 운영 두뇌 + voice interface`로 완성하는 첫 릴리즈입니다.

이번 Release의 질문은 하나입니다.

`상단장님이 손으로 열고 누르지 않아도, 말로 진행 / 보류 / 요약 / 설명을 받을 수 있는가`

## 이번 릴리즈가 해결해야 하는 문제

Phase 5까지 오면 시각 증거와 판단은 좋아졌지만, 상단장님은 여전히 아래를 손으로 처리해야 합니다.

- 진행 버튼 누르기
- 멈춤 이유 열어보기
- 마지막 판단 확인하기
- 짧은 브리핑 읽기

Release 6은 이걸 `voice command + spoken briefing`으로 줄이는 데 집중합니다.

## 제품 목표

### 1) Voice Input Foundation

- push-to-talk
- transcript 생성
- command normalization

### 2) Voice Action Routing

- continue / pause / summary / why-paused / settings-open 같은 핵심 동작 연결

### 3) Spoken Briefing UX

- 현재 상태
- 마지막 판단
- 마지막 visual contradiction
- 다음 행동

위 네 가지를 짧고 일관된 말로 읽어줍니다.

### 4) Voice Safety

- 위험한 명령은 확인 후 실행
- transcript confidence가 낮으면 실행보다 clarification
- voice mode가 Codex-first 흐름을 깨지 않도록 가드

## 포함 범위

- push-to-talk capture shell
- transcription and command normalizer
- voice intent router
- spoken briefing composer
- voice confirmation gate
- device / mode settings
- release 6 smoke suite

## 제외 범위

- 완전한 wake word
- 항상 듣는 background listener
- 장시간 실시간 full-duplex assistant
- App Server 직접 제어
- Codex execution 대체

## 핵심 기능 기준

### voice capture

- 버튼 또는 단축 진입으로 짧게 말하고 끊을 수 있어야 함

### voice intent

- 음성 명령을 구조화 intent로 만들 수 있어야 함

### spoken briefing

- popup / judgment / visual과 같은 뜻을 읽어줘야 함

### safety

- high-risk action은 confirmation 없이는 실행되지 않아야 함

## 성공 기준

### 사용자 경험 기준

- 상단장님이 `다음 단계 진행`, `왜 멈췄어`, `상태 요약` 정도를 자연스럽게 음성으로 쓸 수 있음
- 말로 들은 내용과 화면의 카드 의미가 다르지 않음
- voice가 새 기능처럼 느껴지기보다 `기존 javis를 더 편하게 쓰는 입구`처럼 느껴짐

### 제품 기준

- voice event가 intent -> action -> spoken feedback 흐름으로 이어짐
- pause / ask_user / retry / continue가 음성에서도 안전 규칙을 유지함
- wake word 전 단계로서 충분한 voice-ready 구조가 생김

## 주요 리스크

### 1) transcript가 애매해 잘못 실행될 수 있음

- 해결 방향: intent confidence / confirmation / repeat flow

### 2) 말로 읽는 브리핑이 장황할 수 있음

- 해결 방향: briefing contract와 길이 제한

### 3) voice가 기존 Codex-first 구조를 우회할 수 있음

- 해결 방향: action router 재사용, safety gate 재사용

## 주요 산출물

- Voice Interaction Contract v1
- Push-to-Talk Surface v1
- Voice Intent Router v1
- Spoken Briefing Composer v1
- Voice Safety Guard v1

## 완료 선언 조건

1. 핵심 음성 명령이 기존 action router와 연결되어 있음
2. spoken briefing이 judgment / visual 상태를 재사용해 읽어줌
3. 위험 명령 confirmation 흐름이 존재함
4. Release 6 smoke 시나리오가 반복 검증 가능함
