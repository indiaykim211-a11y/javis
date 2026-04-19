# Phase 4: Judgment Overlay

## 단계 목적

이 단계의 목적은 `javis`가 Phase 3에서 정리한 `no automation / thread automation / project automation` 운영 흐름 위에 `판단 오버레이`를 얹는 것입니다.

핵심은 아래 한 줄입니다.

`Codex가 실행하고, javis는 그 결과를 구조화해서 OpenAI에게 판단받고, 로컬 런타임이 안전하게 집행한다.`

## 왜 이 단계가 필요한가

Phase 3까지 오면 `javis`는 아래를 꽤 잘하게 됩니다.

- 어떤 운영 모드가 맞는지 추천
- Codex 앱으로 바로 옮길 수 있는 launch-ready prompt 준비
- 결과를 다시 어디서 볼지 안내
- automation을 과하게 쓰지 않도록 safety guard 제공

하지만 아직 가장 중요한 한 가지가 남아 있습니다.

- `지금 Codex 결과가 괜찮은지`
- `계속 가도 되는지`
- `같은 단계를 다시 보정해야 하는지`
- `상단장님을 불러야 하는지`

이 판단은 아직 상단장님이 직접 하거나, 매우 얇은 규칙으로만 처리됩니다.

Phase 4는 바로 이 빈틈을 메웁니다.

## 이 단계의 기본 철학

### 1. 판단은 overlay다

OpenAI 판단 엔진은 `Codex를 대체하는 새 실행기`가 아닙니다.

- 코드 작성과 실행은 여전히 Codex가 맡습니다.
- 판단 엔진은 `그 결과를 해석하고 분기시키는 상위 계층`입니다.

### 2. 판단은 운영 모드를 존중해야 한다

Phase 4의 판단 엔진은 항상 아래를 알고 있어야 합니다.

- 지금이 `no automation`인지
- `thread automation` follow-up인지
- `project automation` 독립 결과인지

즉 모든 판단은 `운영 모드 문맥`을 포함해야 합니다.

### 3. 자유서술이 아니라 구조화 응답이 기본이다

이 단계의 핵심은 모델이 말을 잘하는 것이 아니라, 앱이 안전하게 읽을 수 있는 결정을 주는 것입니다.

- `continue`
- `wait`
- `retry`
- `pause`
- `ask_user`

이 다섯 가지를 중심으로 제품이 흔들리지 않게 설계합니다.

### 4. 위험과 확신은 항상 같이 본다

같은 `continue`라도 아래는 다릅니다.

- 확신 높고 위험 낮은 continue
- 확신 낮고 위험 중간인 continue

Phase 4에서는 `결정`만이 아니라 `confidence / risk / user message / follow-up action`을 함께 다룹니다.

## 이 단계에서 javis가 맡을 것

### 1. Judgment Packet Builder

현재 프로젝트, 운영 모드, 정책, 최근 결과, 최근 증거를 묶어 구조화 입력으로 만듭니다.

### 2. Judgment Prompt Assembly

운영 마스터, 진행 정책, 안전 정책, 보고 정책을 역할별로 조합합니다.

### 3. Structured Response Validation

모델 응답이 계약을 어기면 그대로 믿지 않고 `pause` 쪽으로 강등합니다.

### 4. Decision Surface

상단장님이 바로 이해할 수 있도록 팝업과 Control Center에 아래를 보여줍니다.

- 현재 판단
- 이유
- 확신
- 위험
- 다음 행동

### 5. Decision Routing

판단 결과에 따라 아래를 연결합니다.

- continue면 다음 단계 또는 다음 follow-up
- retry면 Codex 재지시 초안
- ask_user면 상단장님 호출
- pause면 자동 진행 멈춤

### 6. Judgment History

최근 판단과 그 근거를 짧게 남겨서, 왜 멈췄는지 나중에 추적할 수 있게 합니다.

## 이 단계에서 javis가 직접 하지 않을 것

- 브라우저 화면 자체를 깊게 읽는 것
- OCR / 비전 추론
- 음성 입출력
- App Server 직접 연동
- Codex가 이미 가진 실행기능 재구현

즉, Phase 4는 `눈과 귀`보다 먼저 `두뇌의 분기 로직`을 만드는 단계입니다.

## 이 단계에서 Codex가 맡는 것

- 코드 작성 / 수정 / 검증
- 같은 스레드 순차 진행
- thread automation follow-up
- project automation 독립 실행
- worktree / Triage / 결과 큐

## 이 단계에서 OpenAI 판단 엔진이 맡는 것

- 현재 결과 해석
- continue / wait / retry / pause / ask_user 결정
- 이유와 위험도 설명
- 상단장님용 짧은 메시지 생성
- 필요 시 Codex용 재지시 문구 생성

## 핵심 사용자 시나리오

### 시나리오 A. 같은 스레드 순차 진행 판단

- Codex가 현재 티켓을 끝냈다고 보고
- `javis`가 현재 단계 목표와 정책을 묶어 판단 요청
- 판단 엔진이 `continue` 또는 `retry`를 반환

### 시나리오 B. thread automation follow-up 판단

- heartbeat 결과가 다시 올라옴
- `javis`가 현재 상태를 요약해 판단
- 상단장님은 계속 둘지, 멈출지, 같은 스레드에서 재지시할지 이해

### 시나리오 C. project automation triage 판단

- nightly brief, smoke, CI triage 결과가 독립적으로 올라옴
- `javis`는 그 결과를 읽고 `다시 같은 운영 스레드로 넘길지`, `pause할지`, `ask_user할지` 정리

### 시나리오 D. 낮은 확신 / 높은 위험

- 결과 자체는 있어 보이지만 판단 확신이 낮음
- `javis`는 무리하게 continue하지 않고 `ask_user` 또는 `pause`로 보수적으로 대응

## 완료 조건

- `Codex 결과를 어떻게 해석할지`가 제품 안에서 구조화됨
- 판단 입력과 출력이 계약 기반으로 고정됨
- 상단장님이 `왜 계속 가는지 / 왜 멈췄는지`를 바로 이해 가능
- retry / ask_user / pause 분기가 UI와 로컬 런타임에 자연스럽게 연결됨
- Release 5에서 화면 인식 입력을 붙일 자리가 이미 준비됨

## 다음 연결 문서

- `../releases/release-4-judgment-beta.md`
- `../ai/openai-judgment-engine-v1.md`
- `../ai/prompt-policy-v1.md`
- `../specs/judgment-input-contract-v1.md`
- `../specs/judgment-response-contract-v1.md`
