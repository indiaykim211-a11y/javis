# Sprint 10: Judgment Foundation

## 스프린트 목표

Phase 3 운영 흐름 위에 얹을 OpenAI 판단 엔진의 입력/출력 바닥을 만듭니다.

## 포함 티켓

- `R4-001` judgment packet builder
- `R4-002` judgment prompt assembly
- `R4-003` structured response validator

## 상세 목표

### 1) 입력을 구조화

- 현재 프로젝트
- 현재 단계
- 운영 모드
- 정책
- 최근 결과 / triage / runboard 요약

을 모델 입력용 packet으로 묶을 수 있어야 합니다.

### 2) 응답을 검증

- 허용되지 않은 decision
- 필수 필드 누락
- high risk continue

같은 위험 응답은 제품이 그대로 믿지 않게 해야 합니다.

## 완료 조건

- judgment input contract를 실제 제품 입력 흐름으로 연결 가능
- judgment response contract를 validator로 해석 가능

## 스프린트 산출물

- Judgment Packet Builder v1
- Judgment Prompt Assembly v1
- Structured Response Validator v1
