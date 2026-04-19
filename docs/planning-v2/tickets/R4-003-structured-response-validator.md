# R4-003: structured response validator

## 목적

모델 응답이 계약을 어길 때 그대로 집행하지 않고, pause 쪽으로 안전하게 강등합니다.

## 사용자 스토리

상단장님으로서, 판단 엔진이 말을 이상하게 해도 앱이 위험하게 움직이지 않길 원합니다.

## 범위

- decision enum 검증
- 필수 필드 검증
- high risk continue 강등
- retry without prompt 강등

## 완료 조건

- 잘못된 judgment 응답이 자동 집행으로 이어지지 않음

## 의존성

- `R4-001`
- `R4-002`
- `judgment-response-contract-v1`

## 예상 난이도

- `M`
