# Release 8: Live Ops Beta

## 릴리즈 미션

`Release 8`의 목표는 `javis`를 "Codex를 잘 쓰게 도와주는 앱"에서 `Codex 운영을 실제로 굴리는 라이브 오퍼레이터`로 한 단계 더 끌어올리는 것입니다.

## 이번 릴리즈가 해결해야 하는 문제

지금까지는 전략, integration, 판단, 시각, 음성까지 잘 붙었습니다.

하지만 실제 운영에서는 이런 질문이 계속 생깁니다.

- 지금 launch해야 하나
- 지금은 기다려야 하나
- 결과가 돌아왔으니 어디로 재진입해야 하나
- 지금은 복구보다 관찰이 우선인가
- 지금은 수동 게이트가 필요한가

`Release 8`은 이 질문을 제품 표면에서 바로 답하게 만드는 릴리즈입니다.

## 포함 범위

- live ops profile
- current lane model
- operations charter
- launchpad
- re-entry brief
- recovery playbook
- shift brief
- release 8 smoke suite

## 제외 범위

- 새 Codex 실행 엔진 자체를 만드는 일
- cloud / app server capability를 실제 네트워크로 강결합하는 일
- 완전 자율 장기 에이전트화

## 성공 기준

1. 상단장님이 "지금 javis가 어떤 운영 상태인지" 바로 이해할 수 있다.
2. Codex 결과가 돌아왔을 때 same-thread / triage / manual gate 중 어디로 갈지 설명할 수 있다.
3. 막혔을 때 recovery 수준을 none / light / guided / manual로 분명히 보여준다.
4. release 8 smoke가 통과한다.
