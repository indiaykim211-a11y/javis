# Release 6. Intelligence Studio Beta

## 릴리즈 정의

`Release 6`은 web shell이 `운영 화면`을 넘어서 `운영 두뇌 편집기`까지 갖추는 단계입니다.

`Phase 5`까지는 프로젝트와 운영 흐름 중심이었다면, 이번 릴리즈부터는 판단/시각/음성/딥 인티그레이션 설정이 모두 `Control Deck`으로 올라옵니다.

## 사용자 가치

- 상단장님이 Tk 레퍼런스 창을 자주 열지 않아도 됩니다.
- 현재 세션이 어떤 판단 규칙과 시각 기준, 음성 응답 규칙으로 돌아가는지 웹에서 바로 파악할 수 있습니다.
- Codex-first 운영 전략과 판단 레이어가 같은 화면 안에서 이어집니다.

## 포함 기능

- intelligence contract
- intelligence 저장 API
- `Intelligence` drawer tab
- judgment / visual / voice / deep integration editors
- recent result / timeline cards
- integration observability panels

## 검증 기준

- `python -m compileall app launcher.py`
- `python -m app.api.server --dump-workspace`
- `npm run build`
- intelligence 저장/복원 smoke

## 릴리즈 상태

- 계획: 완료
- 구현: 완료
