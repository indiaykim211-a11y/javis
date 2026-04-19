# H6-001 Intelligence Contract and Endpoint

## 목표

Control Deck payload에 intelligence 영역을 추가하고, web shell이 저장할 수 있도록 endpoint를 확장합니다.

## 완료 조건

- `GET /api/control-deck`가 intelligence payload를 포함한다.
- `GET /api/workspace`가 intelligence payload를 간접 포함한다.
- `POST /api/control-deck`가 `kind = intelligence`를 처리한다.

## 메모

- option 목록은 models 상수를 재사용한다.
- timeline / recent result는 workflow helper를 재사용한다.
