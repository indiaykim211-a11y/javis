# R4-002: judgment prompt assembly

## 목적

운영 마스터, 진행 정책, 보고 정책, 안전 정책을 역할별로 조합해 judgment prompt를 만듭니다.

## 사용자 스토리

상단장님으로서, 판단 엔진이 거대한 프롬프트 한 덩어리가 아니라 정책 시스템 위에서 동작하길 원합니다.

## 범위

- 정책 모듈 조합
- 운영 모드별 문맥 차이 반영
- retry / ask_user 지향 prompt 조합

## 완료 조건

- 현재 프로젝트 기준 judgment prompt 조합 규칙이 정리됨

## 의존성

- `R4-001`
- `prompt-policy-v1`

## 예상 난이도

- `M`
