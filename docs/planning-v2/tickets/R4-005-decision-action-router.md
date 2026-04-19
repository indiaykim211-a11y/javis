# R4-005: decision action router

## 목적

continue / wait / retry / pause / ask_user를 실제 제품 후속 흐름으로 연결합니다.

## 사용자 스토리

상단장님으로서, 판단 결과가 말로만 남지 않고 다음 행동으로 이어지길 원합니다.

## 범위

- continue 후속 연결
- retry 재지시 흐름
- pause / ask_user 분기
- 안전한 집행 조건

## 완료 조건

- 판단 결과가 실제 사용자 액션 또는 로컬 런타임 흐름으로 이어짐

## 의존성

- `R4-003`
- `R4-004`

## 예상 난이도

- `M`
