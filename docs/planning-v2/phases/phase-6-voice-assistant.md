# Phase 6: Voice Assistant

## 단계 목적

이 단계의 목적은 `javis`를 `말로 지시하고, 말로 보고받는 상위 어시스턴트`로 올리는 것입니다.

핵심은 새 두뇌를 만드는 것이 아니라, 이미 있는 흐름을 더 자연스럽게 쓰게 만드는 것입니다.

- Codex는 계속 실행 엔진을 맡습니다.
- `javis`는 계속 상위 감독과 오케스트레이션을 맡습니다.
- Voice Layer는 그 위에 올라가는 `입과 귀` 역할입니다.

즉, Phase 6은 `Codex-first + Judgment + Visual Supervisor` 위에 `Voice Interface`를 얹는 단계입니다.

## 왜 이 단계가 필요한가

Phase 5까지 오면 `javis`는 이미 아래를 할 수 있습니다.

- Codex-first 운영 전략 선택
- automation mode 판단
- judgment 기반 continue / retry / ask_user
- visual contradiction 기반 재판단

하지만 여전히 상단장님은 손으로 눌러야 하는 순간이 많습니다.

- 지금 상태를 빨리 듣고 싶을 때
- `다음 단계 진행해`를 바로 말하고 싶을 때
- `왜 멈췄어`, `지금 뭐 보고 있어`를 묻고 싶을 때
- Control Center를 열지 않고 한 줄 요약만 받고 싶을 때

Phase 6은 이 간격을 메웁니다.

## 이 단계의 기본 철학

### 1. Voice는 새 판단 엔진이 아니라 상위 인터페이스다

Voice Layer가 따로 판단을 모두 가져가면 구조가 꼬입니다.

그래서 원칙은 아래와 같습니다.

- 판단은 기존 Judgment / Visual Layer를 재사용
- 실행은 기존 action router를 재사용
- Voice는 intent를 만들고, briefing을 읽고, confirmation을 받는 역할

### 2. 시작은 push-to-talk가 맞다

이 단계의 시작은 `항상 듣는 자비스`가 아닙니다.

- 1차: push-to-talk
- 2차: TTS briefing
- 3차: 짧은 standby / ambient readiness
- wake word는 다음 단계 준비 범위로만 다룹니다

이렇게 가야 안정성과 오작동 제어가 쉽습니다.

### 3. Voice는 자유 대화보다 운영 명령에 먼저 맞춘다

초기에는 아래처럼 운영 명령 중심이 좋습니다.

- 다음 단계 진행
- 멈춰 / 보류
- 왜 멈췄어
- 지금 상태 요약해줘
- 마지막 판단 읽어줘
- 마지막 화면 모순 읽어줘
- 설정 열어줘

자연 대화형 assistant는 나중에 더 키워도 됩니다.

### 4. spoken summary는 기존 구조화 상태를 읽어야 한다

Voice 요약이 매번 새로 자유 생성되면 흔들립니다.

그래서 spoken briefing은 아래를 재료로 만듭니다.

- surface state
- last judgment
- last visual result
- current step / next action
- operator pause reason

즉, `보이는 카드`와 `읽어주는 말`이 같은 뜻을 가져야 합니다.

### 5. Voice action은 안전 규칙을 더 강하게 적용한다

음성 명령은 실수 입력 가능성이 높습니다.

그래서 아래 원칙을 둡니다.

- destructive / irreversible action은 바로 실행하지 않음
- retry / continue도 high risk면 confirmation 먼저
- transcript confidence가 낮으면 ask_user 또는 repeat
- 애매한 intent는 실행보다 clarification

## 이 단계에서 javis가 맡는 것

### 1. Push-to-Talk Capture Shell

짧게 말하고 끊는 `voice capture` 표면을 만듭니다.

### 2. Transcription and Command Normalizer

음성을 텍스트로 바꾸고, 운영 intent로 정규화합니다.

예:

- `다음 단계 진행해`
- `멈춰`
- `지금 상태 요약해줘`
- `왜 보류야`

### 3. Voice Intent Router

정규화된 intent를 기존 action router와 연결합니다.

즉 voice가 새 행동을 만들기보다, 기존 UI 행동을 음성으로 호출합니다.

### 4. Spoken Briefing Composer

현재 상태를 짧은 음성 보고로 바꿉니다.

### 5. Confirmation Gate

위험하거나 되돌리기 어려운 명령은 음성 확인 단계를 둡니다.

### 6. Voice Device / Mode Settings

마이크, 스피커, 음성 모드, 자동 읽기 여부, standby 상태를 관리합니다.

## 이 단계에서 javis가 직접 하지 않을 것

- 완전한 항상-켜짐 wake word
- 장시간 실시간 full-duplex voice agent
- 사람처럼 긴 자유대화 assistant
- Codex 실행 엔진 대체
- App Server 직접 오케스트레이션

## 이 단계에서 Codex가 맡는 것

- 코드 작성 / 수정 / 실행
- automations / worktree / triage / runboard
- phase / release 흐름에 맞는 실제 개발 진행

## 이 단계에서 OpenAI 음성 계층이 맡는 것

- STT
- TTS
- intent 후보 생성
- spoken summary 문장 보조

단, 최종 실행 허용 여부는 기존 judgment / safety guard가 같이 잡습니다.

## 대표 사용 시나리오

### 시나리오 A. 진행 명령

- 상단장님이 `다음 단계 진행해`라고 말함
- `javis`가 intent를 `continue_step`으로 정규화
- 현재 risk와 pause 상태를 확인
- 안전하면 기존 action router로 계속 진행

### 시나리오 B. 왜 멈췄어

- 상단장님이 `왜 멈췄어`라고 말함
- `javis`가 last judgment / last visual result / pause reason을 묶어
- 한두 문장 브리핑으로 읽어줌

### 시나리오 C. 상태 요약

- 상단장님이 `지금 상태 요약해줘`라고 말함
- popup summary와 같은 뜻의 음성 브리핑을 읽어줌

### 시나리오 D. 애매한 음성

- transcript confidence가 낮음
- intent가 두 개 이상으로 걸림
- `javis`는 실행하지 않고 다시 말해달라고 요청

## 완료 조건

- push-to-talk로 음성 입력을 받고 command intent까지 연결할 수 있음
- continue / pause / summary / why-paused 같은 핵심 음성 명령이 동작함
- spoken briefing이 popup / judgment / visual state와 같은 뜻을 유지함
- high-risk 명령은 confirmation 없이 실행되지 않음
- wake word 이전 단계로서 `voice-ready assistant` 체감이 생김

## 다음 연결 문서

- `../releases/release-6-voice-beta.md`
- `../specs/voice-interaction-contract-v1.md`
- `../phases/phase-5-visual-supervisor.md`
