# H3-001 Action API Contract

## 목표

web shell이 Python 엔진 액션을 호출할 수 있는 공통 JSON 계약을 정의합니다.

## 완료 조건

- `/api/action`
- `actionId`
- `message`
- `payload`
- `snapshot`

## 액션 범위

- continue
- start_auto
- pause_auto
- resume_ready
- refresh_windows
- focus_codex
- capture_now
- voice_brief
- rejudge
- retry_now
