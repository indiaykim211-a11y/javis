# Release 5 Priority Board

## 우선순위 기준

- `P0`
  - Release 5의 정체성을 결정하는 필수 항목
- `P1`
  - 시각 판단 신뢰도와 제품 체감을 크게 높이는 핵심 항목
- `P2`
  - 있으면 좋지만 일부는 다음 릴리즈로 이월 가능한 항목

## 우선순위 보드

| Ticket | 우선순위 | 스프린트 | 가치 | 리스크 | 선행 의존성 |
| --- | --- | --- | --- | --- | --- |
| `R5-001` capture target planner | P0 | Sprint 13 | 매우 높음 | 중간 | `R4-001`~`R4-008` |
| `R5-002` visual evidence packet builder | P0 | Sprint 13 | 매우 높음 | 중간 | `R5-001` |
| `R5-003` browser and Codex observation prompts | P0 | Sprint 13 | 높음 | 중간 | `R5-001`, `R5-002` |
| `R5-004` visual summary surface | P1 | Sprint 14 | 높음 | 중간 | `R5-002`, `R5-003` |
| `R5-005` claim vs screen contradiction detector | P1 | Sprint 14 | 매우 높음 | 높음 | `R5-002`, `R5-003`, `R5-004` |
| `R5-006` visual rejudge bridge | P1 | Sprint 14 | 매우 높음 | 높음 | `R5-004`, `R5-005` |
| `R5-007` privacy and capture safety guard | P1 | Sprint 15 | 높음 | 중간 | `R5-001`~`R5-006` |
| `R5-008` Release 5 smoke suite | P1 | Sprint 15 | 높음 | 낮음 | 전체 |

## 구현 순서 메모

- `R5-001`~`R5-003`이 있어야 시각 입력이 과하지 않게 설계됩니다.
- `R5-004`~`R5-006`은 상단장님이 실제로 `화면도 본다`고 느끼는 구간입니다.
- `R5-007`이 없으면 Release 5는 캡처 남발과 민감 정보 저장 위험이 커집니다.
- `R5-008`이 있어야 시각 판단 흐름을 반복 점검할 수 있습니다.
