# R5-006: visual rejudge bridge

## 목적

시각 증거를 기존 판단 엔진에 다시 넣어 최종 continue / retry / ask_user를 재판정합니다.

## 사용자 스토리

상단장님으로서, 화면을 본 뒤에는 텍스트만 봤을 때와 다른 더 정확한 판단을 받길 원합니다.

## 범위

- visual evidence -> judgment overlay 재입력
- contradiction 후속 분기
- visual retry / ask_user 브리지

## 완료 조건

- 시각 증거가 들어간 후 판단 결과가 제품 흐름에 실제 반영됨

## 의존성

- `R5-004`
- `R5-005`

## 예상 난이도

- `M`
