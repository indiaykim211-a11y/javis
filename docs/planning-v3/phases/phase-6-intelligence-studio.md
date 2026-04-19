# Phase 6. Intelligence Studio

## 목표

웹 셸의 `Control Deck` 안에서 `판단`, `시각 감독`, `음성`, `Deep Integration` 설정과 최근 결과를 한 번에 다루는 `Intelligence Studio`를 올립니다.

핵심은 새 두뇌를 만드는 것이 아니라, 이미 Python 엔진 안에 들어 있는 판단 레이어를 `web shell`에서 읽고 저장하고 다시 조정할 수 있게 여는 것입니다.

## 왜 지금 필요한가

- `Phase 5`에서 workspace bundle과 live sync가 안정화되었습니다.
- 이제 상단장님이 실제로 쓰려면, 운영 두뇌 쪽 설정도 웹에서 만질 수 있어야 합니다.
- Tk 기준으로만 존재하던 `판단 / 시각 / 음성 / 딥 인티그레이션` 패널을 웹으로 올려야 `진짜 주 사용 화면`이 웹 셸로 바뀝니다.

## 사용자 경험

- `Control Deck` 안에 `Intelligence` 탭이 추가됩니다.
- 이 탭에서 아래 4개 영역을 한 번에 봅니다.
  - `Judgment Studio`
  - `Visual Studio`
  - `Voice Studio`
  - `Integration Studio`
- 각 영역은 `현재 설정 + 최근 결과 + 히스토리 / 타임라인`을 함께 보여줍니다.
- 저장은 한 번에 `Intelligence 저장`으로 끝내고, live sync가 켜져 있어도 편집 중 draft는 덮어쓰지 않습니다.

## 포함 범위

- `control deck` payload에 intelligence contract 추가
- `POST /api/control-deck`에 intelligence 저장 지원
- web shell drawer에 `Intelligence` 탭 추가
- 판단/시각/음성/딥 인티그레이션 설정 편집기
- 최근 결과 / timeline / handoff / observability 패널 노출
- dirty guard와 저장 후 재동기화

## 제외 범위

- 실제 OpenAI API 연결
- 실시간 마이크 캡처
- 실시간 시각 추론 스트리밍
- websocket 기반 push sync

## 완료 기준

- web shell에서 `judgment`, `visual`, `voice`, `deep integration` 값을 읽을 수 있다.
- web shell에서 값을 수정해 저장하면 Python 세션에 반영된다.
- 최근 judgment / visual / voice 결과와 timeline이 Control Deck에서 보인다.
- capability registry / handoff / observability 텍스트를 웹에서 볼 수 있다.
- live sync 중에도 intelligence draft는 안전하게 보존된다.

## 티켓 분해

1. `H6-001` Intelligence contract and endpoint
2. `H6-002` Judgment Studio
3. `H6-003` Visual Studio
4. `H6-004` Voice and Integration Studio
5. `H6-005` Intelligence sync guards
6. `H6-006` Phase 6 verification
