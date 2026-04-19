# Release 5: Visual Beta

## 릴리즈 미션

`javis`를 `Codex 결과 + 시각 증거`를 함께 읽는 감독형 어시스턴트로 끌어올립니다.

이 릴리즈의 본질은 아래입니다.

- 화면 인식을 새 기능처럼 따로 붙이는 것이 아니라
- Phase 4 판단 루프에 `시각 근거`를 추가해
- Codex 말과 실제 화면이 다를 때 더 안전하게 멈추는 것

## 이 릴리즈가 해결해야 하는 문제

Release 4까지 끝나면 `javis`는 말과 로그는 꽤 잘 읽습니다.

하지만 아직 아래는 약합니다.

- 실제 브라우저 화면이 기대와 맞는지
- Codex 완료 보고와 실제 UI가 일치하는지
- 비어 있는 페이지, 에러 배너, 잘못된 버튼 상태 같은 시각 이상 신호
- retry가 필요한지 ask_user가 필요한지 시각 근거로 확신을 올리는 것

Release 5는 이 약점을 `targeted capture + visual evidence + contradiction detection`으로 메웁니다.

## 핵심 사용자 시나리오

1. 상단장님이 현재 프로젝트를 불러옵니다.
2. Codex는 같은 스레드 또는 automation 결과를 남깁니다.
3. `javis`는 먼저 텍스트/네이티브 근거로 판단 가능 여부를 봅니다.
4. 근거가 부족하거나 모순이 보이면 필요한 화면만 캡처 대상으로 고릅니다.
5. 시각 요약을 판단 엔진에 다시 넣습니다.
6. 앱은 continue / retry / ask_user를 더 설득력 있게 보여주고 연결합니다.

## Release 5의 제품 목표

### 1) Visual Evidence Foundation

- 무엇을 캡처할지 먼저 고를 수 있어야 합니다.
- Codex 창 / 브라우저 / 특정 영역을 목적별로 구분할 수 있어야 합니다.

### 2) Claim vs Screen Verification

- Codex 설명과 실제 화면이 일치하는지 확인할 수 있어야 합니다.
- mismatch가 보이면 continue를 쉽게 주지 않아야 합니다.

### 3) Visual Decision UX

- 팝업에서 `무엇을 봤고 왜 이상한지`가 짧게 보여야 합니다.
- Control Center에서는 evidence digest와 재판단 흐름이 보여야 합니다.

### 4) Safe Capture Operations

- 민감한 화면이나 불필요한 전체 캡처를 남발하지 않아야 합니다.
- 필요한 근거만 짧게 저장하고 재사용해야 합니다.

## 포함 범위

- capture target planner
- visual evidence packet builder
- Codex / browser observation prompt
- visual summary surface
- claim vs screen contradiction detector
- visual rejudge bridge
- privacy / capture safety guard

## 제외 범위

- 음성 입출력
- 완전한 브라우저 테스트 자동화 재구현
- App Server 직접 연동
- 전면적인 OCR 플랫폼 구축
- Codex 실행 엔진 대체

## 필수 기능 기준

### visual evidence packet

- 현재 단계, 기대 결과, 캡처 대상, 관찰 포인트를 같이 묶을 수 있어야 함

### contradiction detection

- Codex가 성공이라 말해도 화면이 실패면 mismatch로 드러나야 함

### visual rejudge

- 시각 evidence가 들어간 후 판단이 다시 갱신돼야 함

### visual UX

- 팝업에서 한 줄 요약
- Control Center에서 evidence digest / contradiction / follow-up이 보여야 함

## 성공 기준

### 사용자 경험 기준

- 상단장님이 `왜 화면 때문에 멈췄는지` 바로 이해할 수 있음
- Codex 결과와 실제 브라우저 상태가 어긋날 때 javis가 더 믿을 만해짐
- 눈으로 봐야만 알 수 있던 이상 신호를 덜 놓침

### 제품 기준

- javis가 `텍스트 판단기`에서 `시각 감독자`로 올라감
- Release 6에서 음성과 같은 판단 엔진을 공유할 준비가 됨
- Codex-first 전략을 깨지 않고도 화면 근거를 필요할 때만 사용할 수 있음

## 주요 산출물

- Visual Evidence Pipeline v1
- Claim vs Screen Verification v1
- Visual Decision Surface v1
- Capture Safety Guard v1

## 주요 리스크

### 1) 화면을 너무 많이 읽으려 할 수 있음

- 해결 방향: capture target planner + 최소 캡처 원칙

### 2) 시각 요약이 장황해질 수 있음

- 해결 방향: observation prompt를 판정 중심으로 제한

### 3) 시각 신호가 애매한데도 과감히 진행할 수 있음

- 해결 방향: contradiction / confidence / risk를 함께 판단

## Release 5 완료 선언 조건

1. 필요한 화면만 골라 visual evidence packet을 만들 수 있음
2. Codex 주장과 실제 화면의 mismatch를 탐지할 수 있음
3. 시각 증거를 포함한 재판단이 팝업과 Control Center에 자연스럽게 보임
4. 상단장님 기준으로 `이제 javis가 화면도 보고 판단해 준다`는 체감이 생김
