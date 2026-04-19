# R4-001: judgment packet builder

## 목적

현재 프로젝트, 운영 모드, 정책, 최근 결과를 OpenAI 판단 엔진에 넣을 구조화 입력으로 묶습니다.

## 사용자 스토리

상단장님으로서, 모델이 아무 정보나 받는 것이 아니라 `지금 판단에 필요한 정보만 안정적으로` 받길 원합니다.

## 범위

- project context
- runtime context
- policy context
- evidence digest
- automation mode / triage 문맥 포함

## 완료 조건

- 현재 프로젝트 기준 judgment input 초안을 안정적으로 만들 수 있음

## 의존성

- `R3-001`~`R3-008`
- `judgment-input-contract-v1`

## 예상 난이도

- `M`
