# Release 5 Smoke Checklist v1

## 목적

Release 5의 핵심인 `visual evidence -> contradiction detection -> visual rejudge` 흐름을 5~10분 안에 반복 점검합니다.

## 준비

- `javis` 실행
- 테스트용 프로젝트 / 단계 / 최근 상태 준비
- 가능하면 Codex 창과 브라우저 결과 화면을 함께 띄워 둠

## 시나리오 A: visual continue

1. 현재 단계와 기대 화면을 넣는다.
2. 브라우저 / Codex 화면이 정상 상태인 캡처를 준비한다.
3. visual evidence packet을 만든다.
4. visual rejudge를 실행한다.

기대 결과:

- visual summary에 정상 상태가 짧게 보인다.
- contradiction가 없다.
- 최종 판단이 continue 쪽으로 유지된다.

## 시나리오 B: claim vs screen mismatch

1. Codex는 완료처럼 보이게 한다.
2. 브라우저는 빈 화면, 오류 배너, 잘못된 라우팅 상태를 준비한다.
3. visual evidence를 붙여 재판단한다.

기대 결과:

- contradiction가 명확하게 표시된다.
- continue 대신 retry 또는 ask_user가 나온다.

## 시나리오 C: 애매한 시각 신호

1. 시각 근거가 충분히 선명하지 않은 캡처를 준비한다.
2. 텍스트 근거도 결정적이지 않게 둔다.
3. visual rejudge를 실행한다.

기대 결과:

- 억지 continue보다 pause / ask_user를 우선한다.
- 확신 낮음이 제품 안에 보인다.

## 시나리오 D: 과한 캡처 방지

1. 전체 화면 캡처를 반복해서 요청하는 상황을 만든다.
2. capture target planner를 다시 확인한다.

기대 결과:

- 필요한 화면만 읽는 방향으로 planner가 유지된다.
- privacy / capture safety guard가 보인다.

## 시나리오 E: 시각 판단 이력

1. visual continue, mismatch, ask_user 흐름을 각각 한 번씩 만든다.
2. 타임라인이나 evidence digest를 다시 본다.

기대 결과:

- 최근 시각 판단 1~N개를 이해할 수 있다.
- 왜 멈췄는지 / 왜 retry인지 다시 추적 가능하다.

## 통과 기준

- visual evidence packet이 현재 단계와 기대 화면을 함께 담는다.
- Codex 주장과 실제 화면의 mismatch를 잡을 수 있다.
- visual rejudge가 최종 판단에 반영된다.
- privacy / capture safety guard가 제품 안에서 드러난다.
- 상단장님 기준으로 `이제 javis가 화면도 감독한다`는 체감이 생긴다.
