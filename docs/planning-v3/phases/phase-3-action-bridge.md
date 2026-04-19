# Phase 3. Action Bridge

## 목표

웹 셸이 `읽기 전용` 표면을 넘어서 Python 엔진 액션을 실제로 호출할 수 있게 만듭니다.

## 핵심 가치

- Assistant Surface에서 바로 진행, 보류, 재개, 브리핑, 재판단, 캡처가 가능합니다.
- web shell이 단순 뷰어가 아니라 `운영 제어 패널`이 됩니다.
- Codex 제어는 계속 Python 엔진이 담당하고, web shell은 고급 UX와 제어 진입점을 맡습니다.

## 포함 범위

- `/api/action` POST 엔드포인트
- action contract
- background auto loop bridge
- action feedback surface
- Control Deck drawer preview

## 제외 범위

- 전체 Control Deck의 완전 이관
- websocket push
- deep integration/App Server 단계

## 완료 기준

- web shell 버튼이 Python 엔진 액션을 실제로 호출합니다.
- continue / pause / resume / refresh / focus / capture / brief / rejudge / retry 가 동작합니다.
- auto loop start / stop 이 local API 서버 안에서 유지됩니다.
- action 결과가 화면에 피드백됩니다.
