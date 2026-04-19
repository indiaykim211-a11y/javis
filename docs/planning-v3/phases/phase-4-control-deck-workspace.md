# Phase 4. Control Deck Workspace

## 목표

웹 셸 안의 `Control Deck`를 미리보기 drawer가 아니라, 실제로 프로젝트와 운영 설정을 다루는 작업공간으로 올립니다.

## 핵심 가치

- 이제 웹 셸만으로도 프로젝트 요약, 목표, 단계 목록을 수정하고 저장할 수 있습니다.
- Codex 전략, automation mode, 운영 cadence 같은 실사용 설정을 Tk 앱 없이도 조정할 수 있습니다.
- 현재 단계 프롬프트를 웹 셸에서 검토하고 다듬은 뒤 바로 이어서 진행할 수 있습니다.
- 최근 프로젝트를 다시 불러오는 흐름이 웹 셸 안에서 닫히기 시작합니다.

## 포함 범위

- `/api/control-deck` 읽기 API
- project / operations / prompt / recent project 저장·복원 엔드포인트
- web shell Control Deck tabs
- project & plan editor
- operations editor and runbook panels
- prompt workbench
- recent project restore surface

## 제외 범위

- websocket 실시간 push
- Electron 네이티브 메뉴/단축키 심화
- OpenAI 판단 엔진의 실제 API 연결
- 시각/음성 고급 설정 전체 이관

## 완료 기준

- 웹 셸에서 프로젝트 요약, 목표, 단계 목록을 수정하고 저장하면 Python 세션에 즉시 반영됩니다.
- 웹 셸에서 Codex 전략 preset/mode, 운영 cadence, dry run, 운영 메모를 저장할 수 있습니다.
- 현재 단계 프롬프트 draft를 웹 셸에서 편집하고 원문으로 되돌릴 수 있습니다.
- 최근 프로젝트를 웹 셸에서 다시 불러와 현재 세션으로 복원할 수 있습니다.
- Phase 3 액션 브리지와 충돌 없이 빌드/기본 스모크가 통과합니다.
