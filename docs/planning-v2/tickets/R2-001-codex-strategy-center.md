# R2-001: Codex 전략 센터

## 목적

문서에만 있는 Codex-first 전략을 Control Center 안의 실제 제품 표면으로 끌어옵니다.

## 배경

Release 1까지는 어시스턴트 표면과 Control Center 구조를 만드는 데 집중했습니다. 이제는 `Codex를 어떻게 운영할지`를 앱 안에서 바로 고를 수 있어야 합니다.

## 사용자 스토리

상단장님으로서, 현재 프로젝트에 맞는 Codex 운영 시나리오를 앱 안에서 바로 보고 고르고 싶습니다.

## 범위

- `Codex 전략` 전용 섹션 추가
- 상위 시나리오 프리셋 라이브러리
- 추천 automation 유형 / cadence / worktree 안내
- 현재 프로젝트 기준 prompt 초안 미리보기
- 클립보드 복사 액션

## 제외

- 실제 automation 생성
- project/worktree 세부 저장 완성형
- OpenAI 판단 엔진 연결

## 구현 메모

- 상단장님 우선순위 시나리오부터 먼저 넣기
- Phase 2 문서와 앱 UI가 같은 언어를 쓰게 하기
- 문서 뷰어가 아니라 `선택 + 이해 + 복사` 흐름이 되게 만들기

## 완료 조건

- 상단장님이 현재 프로젝트에 맞는 Codex 전략을 바로 선택할 수 있음
- prompt 초안을 복사해 Codex에 붙일 수 있음
- Release 3 Automations로 이어질 기반 구조가 보임

## 산출물

- Codex Strategy Center v1

## 의존성

- `R1-004`
- `R1-005`

## 예상 난이도

- `M`
