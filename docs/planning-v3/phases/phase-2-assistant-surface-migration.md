# Phase 2. Assistant Surface Migration

## 목표

Phase 1에서 만든 웹 셸을 `읽기 가능한 데모`에서 `실제 운영 표면` 수준으로 끌어올립니다.

## 핵심 질문

- 지금 Python 엔진이 알고 있는 상태를 웹 셸은 얼마나 풍부하게 받아야 하는가
- 상단장님이 처음 보는 화면에서 무엇이 가장 먼저 보여야 하는가
- Tk 팝업의 핵심 가치 중 무엇을 먼저 웹으로 옮겨야 하는가

## 제품 목표

- 첫 화면만 봐도 `지금 상태 / 왜 그런지 / 다음에 뭘 할지`가 바로 보여야 합니다.
- 지금 단계, 다음 액션, Codex 연결 상태, 최근 프로젝트가 한 화면에서 정리되어야 합니다.
- 아직 액션 브리지가 완전하지 않더라도, UI는 이미 실제 제품처럼 보여야 합니다.

## 포함 범위

- richer snapshot contract
- surface state JSON 노출
- timeline / prompt preview / action dock / deck sections
- 새 Assistant Surface 레이아웃
- refresh / empty / offline / error 상태

## 제외 범위

- 실제 continue/pause/rejudge 액션 호출
- 모든 Control Deck 탭의 React 이관
- websocket push

## 완료 기준

- `/api/snapshot`이 surface 중심 JSON을 반환한다.
- 웹 셸이 status hero, timeline, prompt preview, deck summary를 표시한다.
- 연결이 끊겼을 때도 제품답게 fallback UI가 유지된다.
