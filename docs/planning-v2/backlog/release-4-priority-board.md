# Release 4 Priority Board

## 우선순위 기준

- `P0`
  - Release 4의 정체성을 결정하는 필수 항목
- `P1`
  - 판단 품질과 운영 신뢰도를 크게 높이는 핵심 항목
- `P2`
  - 있으면 좋지만 일부는 다음 릴리즈로 이월 가능한 항목

## 우선순위 보드

| Ticket | 우선순위 | 스프린트 | 가치 | 리스크 | 선행 의존성 |
| --- | --- | --- | --- | --- | --- |
| `R4-001` judgment packet builder | P0 | Sprint 10 | 매우 높음 | 중간 | `R3-001`~`R3-008` |
| `R4-002` judgment prompt assembly | P0 | Sprint 10 | 매우 높음 | 중간 | `R4-001` |
| `R4-003` structured response validator | P0 | Sprint 10 | 매우 높음 | 높음 | `R4-001`, `R4-002` |
| `R4-004` judgment surface and rejudge flow | P1 | Sprint 11 | 높음 | 중간 | `R4-003` |
| `R4-005` decision action router | P1 | Sprint 11 | 매우 높음 | 높음 | `R4-003`, `R4-004` |
| `R4-006` judgment timeline and evidence digest | P1 | Sprint 11 | 높음 | 중간 | `R4-004` |
| `R4-007` confidence and risk guard | P1 | Sprint 12 | 매우 높음 | 중간 | `R4-005`, `R4-006` |
| `R4-008` Release 4 smoke suite | P1 | Sprint 12 | 높음 | 낮음 | 전체 |

## 구현 순서 메모

- `R4-001`~`R4-003`이 있어야 모델 판단을 믿을 최소 토대가 생깁니다.
- `R4-004`~`R4-006`은 상단장님이 실제로 판단 결과를 체감하는 구간입니다.
- `R4-007`이 없으면 Release 4는 위험하게 공격적인 제품이 될 수 있습니다.
- `R4-008`이 있어야 구조화 판단 흐름을 반복 점검할 수 있습니다.
