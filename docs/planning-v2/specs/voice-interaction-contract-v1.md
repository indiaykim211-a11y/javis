# Voice Interaction Contract v1

## 목적

Voice Layer가 `무슨 말을 들었는지`, `어떤 intent로 해석했는지`, `무슨 말을 다시 읽어줄지`를 같은 계약으로 다루기 위한 문서입니다.

## 입력 계약

### voice_event

- `source`
  - `push_to_talk`
  - `button_replay`
  - `ambient_ready`
- `captured_at`
- `transcript_text`
- `transcript_confidence`
- `language`
- `raw_notes`

### context_snapshot

- `surface_state`
- `last_judgment`
- `last_visual_result`
- `operator_pause_reason`
- `current_step_title`

## 정규화 계약

### normalized_intent

- `intent_id`
  - `continue_step`
  - `pause_run`
  - `status_summary`
  - `why_paused`
  - `read_last_judgment`
  - `read_last_visual`
  - `open_settings`
  - `repeat_briefing`
  - `clarify`
- `confidence`
- `slots`
- `requires_confirmation`
- `clarification_question`

## 출력 계약

### voice_action_result

- `action_id`
- `action_status`
  - `executed`
  - `blocked`
  - `confirmation_required`
  - `clarification_required`
- `message_to_user`
- `spoken_briefing_text`
- `should_speak`
- `should_open_control_center`

## 안전 규칙

- transcript confidence가 낮으면 실행보다 clarification
- high-risk action은 confirmation_required
- spoken briefing은 judgment / visual state와 같은 뜻을 유지
- voice는 기존 action router를 우회하지 않음
