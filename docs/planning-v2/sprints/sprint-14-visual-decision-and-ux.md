# Sprint 14: Visual Decision and UX

## 스프린트 목표

시각 근거를 상단장님이 이해할 수 있게 보여주고, Codex 주장과 실제 화면의 모순을 제품 행동으로 연결합니다.

## 포함 티켓

- `R5-004` visual summary surface
- `R5-005` claim vs screen contradiction detector
- `R5-006` visual rejudge bridge

## 상세 목표

### 1) visual summary surface

- 무엇을 봤는지
- 실제 화면이 어땠는지
- 왜 retry / ask_user인지

를 팝업과 Control Center에서 짧게 보여야 합니다.

### 2) contradiction handling

- Codex는 성공이라 하는데 화면은 실패인 경우
- Codex는 완료라 하는데 핵심 CTA가 없는 경우

같은 mismatch가 명확히 드러나야 합니다.

## 완료 조건

- 시각 증거 기반 재판단이 UI와 후속 흐름에 자연스럽게 연결됨

## 스프린트 산출물

- Visual Summary Surface v1
- Claim vs Screen Contradiction Detector v1
- Visual Rejudge Bridge v1
