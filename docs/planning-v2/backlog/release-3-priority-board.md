# Release 3 Priority Board

## 우선순위 기준

- `P0`
  - Release 3의 정체성을 결정하는 필수 항목
- `P1`
  - 운영 완성도를 크게 높이는 핵심 항목
- `P2`
  - 있으면 좋지만 일부는 다음 릴리즈로 이월 가능한 항목

## 우선순위 보드

| Ticket | 우선순위 | 스프린트 | 가치 | 리스크 | 선행 의존성 |
| --- | --- | --- | --- | --- | --- |
| `R3-001` automation mode selector | P0 | Sprint 7 | 매우 높음 | 중간 | `R2-001`~`R2-006` |
| `R3-002` thread automation composer | P0 | Sprint 7 | 매우 높음 | 중간 | `R3-001` |
| `R3-003` project automation composer | P0 | Sprint 7 | 매우 높음 | 중간 | `R3-001` |
| `R3-004` launch checklist / handoff flow | P1 | Sprint 8 | 높음 | 중간 | `R3-002`, `R3-003` |
| `R3-005` automation runboard | P1 | Sprint 8 | 높음 | 중간 | `R3-004` |
| `R3-006` triage summary bridge | P1 | Sprint 8 | 높음 | 중간 | `R3-004` |
| `R3-007` automation safety guard | P1 | Sprint 9 | 높음 | 낮음 | `R3-005`, `R3-006` |
| `R3-008` Release 3 smoke suite | P1 | Sprint 9 | 높음 | 낮음 | 전체 |

## 구현 순서 메모

- `R3-001`이 있어야 상단장님이 automation을 언제 쓰는지부터 판단할 수 있습니다.
- `R3-002`, `R3-003`이 있어야 Phase 3가 말뿐인 전략이 아니라 실제 Codex app handoff로 이어집니다.
- `R3-004`~`R3-006`은 Codex app를 잘 쓰는 javis라는 느낌을 만드는 운영 UX입니다.
- `R3-007`, `R3-008`이 있어야 automation을 과하게 쓰지 않는 제품으로 마감됩니다.
