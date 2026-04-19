# javis Planning Index

## 문서 목적

이 폴더는 `javis`를 실제 개발 가능한 수준으로 집행하기 위한 실행 문서 세트입니다.

상위 비전은 [../javis-master-plan.md](../javis-master-plan.md)에 있고, 이 폴더는 그 계획을 `릴리즈 -> 에픽 -> 스프린트 -> 티켓` 단위로 분해합니다.

## 권장 읽기 순서

1. `releases/release-a-operator-alpha.md`
2. `epics/release-a-epics.md`
3. `ux/operator-console-v1.md`
4. `backlog/release-a-priority-board.md`
5. `sprints/*.md`
6. `tickets/*.md`

## 문서 맵

- `releases/`
  - 릴리즈 목표, 성공 기준, 범위, 리스크
- `epics/`
  - 큰 개발 묶음과 산출물
- `ux/`
  - 제품 경험, 화면 구조, 상호작용 원칙
- `backlog/`
  - 우선순위, 의존성, 스프린트 배치
- `sprints/`
  - 각 스프린트 목표, 완료 조건, 실행 순서
- `tickets/`
  - 실제 구현 단위 작업 문서

## 운영 원칙

- Release A의 목적은 “Codex 운영 보조”가 아니라 “Codex 운영 대체의 시작점”입니다.
- 화면 읽기 전 단계라도, 관찰 가능성과 안전성이 먼저 갖춰져야 합니다.
- 기능 추가보다 `오작동 방지`, `증거 저장`, `사람 개입 지점 설계`를 우선합니다.
- 모든 자동화는 나중에 `Screen Intelligence`로 대체 가능하도록 인터페이스를 분리합니다.

## Release A 한 줄 정의

`상단장님의 현재 수동 역할을 안정적으로 반자동 또는 준자동으로 대신하는 Operator Alpha`
