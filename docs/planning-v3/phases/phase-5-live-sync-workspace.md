# Phase 5. Live Sync Workspace

## 목표

web shell이 `보는 화면`과 `실제 Python 세션 상태` 사이에서 덜 흔들리도록, live sync와 activity feed를 붙여 실사용 신뢰도를 끌어올립니다.

## 핵심 가치

- snapshot과 Control Deck를 따로 읽느라 생기는 drift를 줄입니다.
- 최근 저장/액션/오류 흐름을 activity feed로 바로 볼 수 있습니다.
- 편집 중인 form이나 prompt draft는 자동 동기화가 덮어쓰지 않도록 보호합니다.
- 이제 web shell이 단순 control panel이 아니라 `운영 상태판`처럼 느껴집니다.

## 포함 범위

- `/api/workspace` bundle endpoint
- activity feed payload
- live sync heartbeat
- dirty-state guards
- activity timeline UI

## 제외 범위

- websocket / SSE 기반 push
- Deep Integration / App Server 단계
- 음성/시각 고급 설정 전체 이관

## 완료 기준

- web shell이 하나의 workspace bundle로 snapshot + control deck + activity feed를 함께 읽습니다.
- Control Deck가 열린 상태에서도 편집 중인 영역은 자동 동기화가 바로 덮어쓰지 않습니다.
- 최근 로그/운영 활동이 web shell 안에서 읽기 쉬운 activity feed로 보입니다.
- compile, workspace dump, web build, save/restore smoke가 통과합니다.
