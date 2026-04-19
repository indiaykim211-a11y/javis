# R5-005: claim vs screen contradiction detector

## 목적

Codex가 말한 상태와 실제 화면이 다를 때 그 모순을 명확하게 잡아냅니다.

## 사용자 스토리

상단장님으로서, Codex가 성공이라고 말해도 실제 화면이 아니면 javis가 알아서 멈추길 원합니다.

## 범위

- expected vs observed 비교
- success claim mismatch 탐지
- contradiction severity 분류

## 완료 조건

- 화면 모순이 continue로 흘러가지 않고 retry / ask_user 쪽으로 안전하게 연결됨

## 의존성

- `R5-002`
- `R5-003`
- `R5-004`

## 예상 난이도

- `M`
