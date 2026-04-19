# R4-007: confidence and risk guard

## 목적

low confidence / high risk 상황에서 자동 continue가 과감하게 나가지 않도록 제품 기준을 고정합니다.

## 사용자 스토리

상단장님으로서, javis가 애매한 상황에서 괜히 밀어붙이지 않길 원합니다.

## 범위

- confidence threshold 메모
- high risk 차단 기준
- ask_user 우선 조건
- pause 강등 규칙

## 완료 조건

- 위험/확신 기준이 제품 안에 드러나고, 공격적 자동 진행이 제한됨

## 의존성

- `R4-005`
- `R4-006`

## 예상 난이도

- `S`
