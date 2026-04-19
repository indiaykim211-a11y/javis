# javis Planning v2

## 문서 목적

이 폴더는 `javis 마스터플랜 v2`를 실제 실행 문서로 풀어내기 위한 시작점입니다.

- v1 계획은 운영 콘솔 중심이었다면, v2 계획은 `어시스턴트 중심 제품`을 기준으로 합니다.
- 이번 묶음은 `Phase 1. Assistant Shell`, `Phase 2. Codex-First Foundation`, `Phase 3. Automation Orchestrator`를 실제 집행 가능한 문서로 풀어내는 데 초점을 둡니다.
- 기존 v1 실행 문서는 `docs/planning/`에 그대로 보존합니다.

## 권장 읽기 순서

1. `releases/release-1-assistant-alpha.md`
2. `epics/release-1-epics.md`
3. `ux/assistant-popup-v1.md`
4. `ux/control-center-ia-v1.md`
5. `backlog/release-1-priority-board.md`
6. `checklists/release-1-smoke-checklist-v1.md`
7. `phases/phase-1-assistant-shell.md`
8. `phases/phase-2-codex-first-foundation.md`
9. `releases/release-2-codex-first-beta.md`
10. `epics/release-2-epics.md`
11. `backlog/release-2-priority-board.md`
12. `codex/codex-automations-playbook-v1.md`
13. `codex/javis-codex-automation-scenarios-v1.md`
14. `codex/automation-prompt-templates-v1.md`
15. `ai/openai-judgment-engine-v1.md`
16. `ai/prompt-policy-v1.md`
17. `specs/judgment-input-contract-v1.md`
18. `specs/judgment-response-contract-v1.md`
19. `specs/native-fallback-matrix-v1.md`
20. `checklists/release-2-smoke-checklist-v1.md`
21. `phases/phase-3-automation-orchestrator.md`
22. `releases/release-3-automation-beta.md`
23. `epics/release-3-epics.md`
24. `backlog/release-3-priority-board.md`
25. `sprints/*.md`
26. `tickets/*.md`
27. `checklists/release-3-smoke-checklist-v1.md`

## 현재 문서 맵

- `releases/`
  - 릴리즈 기준 목표, 범위, 완료 조건
- `epics/`
  - 각 Release를 구성하는 큰 개발 묶음
- `backlog/`
  - 우선순위, 가치, 리스크, 스프린트 배치
- `sprints/`
  - 실제 집행 순서와 데모 기준
- `tickets/`
  - 구현 단위 작업 문서
- `phases/`
  - 단계별 제품/개발 상세 방향
- `ux/`
  - 사용자에게 실제로 보일 화면과 상호작용 원칙
- `ai/`
  - OpenAI 판단 엔진 구조와 프롬프트 정책
- `specs/`
  - 엔진 간 주고받는 계약서와 구조화 응답 정의
- `checklists/`
  - 릴리즈 단위 수동/반자동 스모크 체크리스트
- `codex/`
  - Codex 네이티브 기능 활용 전략과 Automations 플레이북

## 이번 라운드에서 정한 핵심

- 메인 제품은 `작은 어시스턴트 팝업`
- 복잡한 제어는 `설정/운영 창`으로 분리
- OpenAI는 `판단 엔진`으로 1차 릴리즈부터 연결
- 화면 인식과 음성은 이후 릴리즈를 위한 전제 구조를 지금부터 고려
- Codex 네이티브 기능은 `새로 만드는 대상`이 아니라 `먼저 끌어다 쓰는 기반`으로 본다

## 이번에 추가된 Control Center 문서

- `ux/control-center-ia-v1.md`
  - 설정/운영 창의 정보구조, 탭 체계, 주요 사용자 흐름

## 이번에 추가된 Release 1 실행 문서

- `epics/release-1-epics.md`
  - Release 1의 큰 개발 묶음 정의
- `backlog/release-1-priority-board.md`
  - 티켓 우선순위와 스프린트 배치
- `sprints/*.md`
  - Sprint 1~3 목표와 완료 조건
- `tickets/*.md`
  - R1-001부터 R1-008까지 구현 단위
- `checklists/release-1-smoke-checklist-v1.md`
  - Release 1을 5~10분 안에 점검하는 기준 시나리오
- `checklists/release-2-smoke-checklist-v1.md`
  - Release 2를 5~10분 안에 점검하는 기준 시나리오

## 이번에 추가된 Release 2 실행 문서

- `releases/release-2-codex-first-beta.md`
  - Codex-first 방향을 제품 안에서 어떻게 구현할지 정리한 릴리즈 문서
- `epics/release-2-epics.md`
  - Release 2를 구성하는 큰 개발 묶음
- `backlog/release-2-priority-board.md`
  - Release 2 티켓 우선순위와 스프린트 배치
- `sprints/sprint-04-codex-strategy-center.md`
  - 전략 센터와 prompt 조합기를 만드는 첫 스프린트
- `sprints/sprint-05-operating-profile-and-runbooks.md`
  - 프로젝트 운영 프로필과 handoff 패널 스프린트
- `sprints/sprint-06-phase-2-readiness.md`
  - native/fallback 경계와 Release 2 검증 스프린트
- `tickets/R2-001` ~ `tickets/R2-006`
  - Phase 2 구현 단위

## 이번에 추가된 Phase 3 / Release 3 실행 문서

- `phases/phase-3-automation-orchestrator.md`
  - no automation / thread / project 판단부터 시작하는 Phase 3 기준 문서
- `releases/release-3-automation-beta.md`
  - Codex app automation 기능을 제품적으로 어떻게 잘 쓰게 만들지 정리한 릴리즈 문서
- `epics/release-3-epics.md`
  - Release 3의 큰 개발 묶음
- `backlog/release-3-priority-board.md`
  - Release 3 티켓 우선순위와 스프린트 배치
- `sprints/sprint-07-automation-authoring.md`
  - automation mode / thread / project composer 스프린트
- `sprints/sprint-08-operations-and-reentry.md`
  - launch flow / runboard / triage bridge 스프린트
- `sprints/sprint-09-automation-readiness.md`
  - safety guard / Release 3 검증 스프린트
- `tickets/R3-001` ~ `tickets/R3-008`
  - Phase 3 구현 단위
- `checklists/release-3-smoke-checklist-v1.md`
  - Release 3을 5~10분 안에 반복 점검하는 기준 시나리오

## 이번에 추가된 판단 엔진 문서

- `ai/openai-judgment-engine-v1.md`
  - javis가 어떤 입력을 받아 어떤 판단을 내릴지
- `ai/prompt-policy-v1.md`
  - 상단장님이 Control Center에서 관리할 프롬프트 정책 계층
- `specs/judgment-input-contract-v1.md`
  - 판단 엔진에 넣을 입력 구조와 정규화 규칙
- `specs/judgment-response-contract-v1.md`
  - 구조화 응답 스키마와 필드 정의
- `specs/native-fallback-matrix-v1.md`
  - Codex 네이티브 우선 / 로컬 fallback 보조 원칙 정리

## 이번에 추가된 Codex-first 전략 문서

- `phases/phase-2-codex-first-foundation.md`
  - 무엇을 Codex에 맡기고 무엇을 javis가 덮을지 정리한 기준 문서
- `codex/codex-automations-playbook-v1.md`
  - Codex Automations를 상단장님 방식에 맞게 쓰는 운영 플레이북
- `codex/javis-codex-automation-scenarios-v1.md`
  - 상단장님 실제 운영 방식에 맞춘 시나리오 묶음
- `codex/automation-prompt-templates-v1.md`
  - 바로 가져다 쓸 수 있는 automation prompt 뼈대
