# Phase 1. Hybrid Foundation

## 목표

Tk 기반 프로토타입에서 바로 모든 것을 갈아엎지 않고, `Python 엔진은 유지 + 웹 셸은 새로 도입`하는 안전한 전환 기반을 만든다.

## 사용자 가치

- 상단장님은 더 세련된 자비스 UI의 시작점을 바로 볼 수 있습니다.
- 앞으로 디자인 투자를 해도 Tk 한계에 묶이지 않습니다.
- 기존 엔진 자산을 버리지 않고 살릴 수 있습니다.

## 포함 범위

- `desktop-shell/` 워크스페이스 생성
- Electron 메인 윈도우
- React/Vite 렌더러
- Python local snapshot API
- 셸에서 프로젝트/단계/상태/최근 프로젝트 읽기
- 자비스 느낌의 시각 디자인 시스템 초안

## 제외 범위

- Electron 셸에서 직접 Codex 제어하기
- 모든 Control Deck 패널의 완전 이관
- 실시간 websocket 스트리밍
- 실제 STT/TTS 장치 연동

## 주요 설계 결정

- Tauri 대신 Electron을 1차 선택으로 둔다.
  - 현재 환경에 Node/npm은 있고 Rust 툴체인은 없다.
  - 그래서 바로 착수 가능한 경로가 Electron이다.
- React 셸은 우선 `읽기 중심`으로 시작한다.
  - 먼저 상태를 잘 보여주고
  - 다음 단계에서 액션 브리지를 붙인다.
- Python API는 매우 얇게 시작한다.
  - `/health`
  - `/api/snapshot`

## 완료 기준

- `npm install` 후 `desktop-shell`이 실행 가능하다.
- Python API에서 snapshot JSON이 나온다.
- React 셸이 API를 읽고 Assistant Surface를 렌더링한다.
- 최소 실행 가이드가 문서화된다.
