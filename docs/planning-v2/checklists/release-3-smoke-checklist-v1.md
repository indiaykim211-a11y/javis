# Release 3 Smoke Checklist v1

## 목적

`Release 3: Automation Beta` 핵심 흐름을 5~10분 안에 반복 점검합니다.

핵심은 아래 5가지입니다.

- 지금 automation이 필요한지 바로 알 수 있는가
- no automation / thread / project 세 가지 흐름이 제품 안에 보이는가
- Codex 앱으로 바로 옮길 수 있는 launch-ready prompt가 나오는가
- 결과를 다시 어디서 봐야 하는지 bridge가 있는가
- automation을 쓰면 안 되는 상황도 safety guard로 보이는가

## 준비

1. PowerShell에서 아래로 실행합니다.

```powershell
cd "C:\Users\ykim2\Desktop\javis"
python launcher.py
```

2. Control Center를 엽니다.
3. `Codex 전략` 섹션으로 이동합니다.

## 시나리오 A: no automation 추천

1. 프로젝트 요약, 목표, 단계 목록을 넣습니다.
2. 프리셋을 `마스터플랜 Follow-up Heartbeat`로 둡니다.
3. mode를 `추천값 따르기`로 둡니다.
4. `프롬프트 새로고침`을 누릅니다.

확인할 것:

- 추천 mode에 `no automation`이 보입니다.
- Launch-ready prompt가 `현재 스레드 순차 진행` 성격으로 나옵니다.
- Launch Checklist가 `automation 없이 현재 스레드에 붙여넣기` 흐름으로 보입니다.
- Runboard에 `지금 무엇을 기다리는가`, `다음 확인 행동`이 보입니다.
- Triage / Re-entry Bridge에 `현재 Codex 운영 스레드`가 보입니다.
- Safety Guard에 `no automation을 먼저 보는 경우`가 보입니다.

## 시나리오 B: thread automation override

1. 같은 프로젝트 상태에서 mode를 `thread automation | 같은 스레드 heartbeat`로 바꿉니다.
2. `프롬프트 새로고침`을 누릅니다.

확인할 것:

- Launch-ready prompt가 thread automation 설명으로 바뀝니다.
- Launch Checklist가 `thread automation 생성 화면` 흐름으로 바뀝니다.
- 결과 확인 위치가 `현재 스레드 + thread automation 결과` 쪽으로 안내됩니다.

## 시나리오 C: project automation

1. 프리셋을 `Nightly Project Brief` 또는 `Release Smoke 자동 점검`으로 바꿉니다.
2. mode를 `project automation | 독립 실행`으로 둡니다.
3. `프롬프트 새로고침`을 누릅니다.

확인할 것:

- Launch-ready prompt가 독립 project automation 설명으로 바뀝니다.
- Launch Checklist에 `standalone / project automation` 흐름이 보입니다.
- Triage / Re-entry Bridge에 `Triage` 또는 `Automations pane` 안내가 보입니다.
- Project Home 카드에 `선택 mode`와 `실제 launch`가 보입니다.

## 저장 / 복원

1. `세션 저장`을 누릅니다.
2. 다른 프로젝트를 저장해 최근 프로젝트 2개 이상을 만듭니다.
3. 이전 프로젝트를 다시 불러옵니다.
4. 앱을 껐다 켭니다.

확인할 것:

- 최근 프로젝트를 불러왔을 때 프리셋과 mode 선택이 같이 복원됩니다.
- 재실행 후에도 Project Home 카드에 mode 정보가 유지됩니다.

## 빠른 자동 스모크

가능하면 아래도 같이 돌립니다.

```powershell
cd "C:\Users\ykim2\Desktop\javis"
python scripts\release_3_smoke.py
```

통과 기준:

- `no automation`, `thread automation`, `project automation` 흐름이 모두 검증됩니다.
- 최근 프로젝트 복원과 재실행 복원이 같이 통과합니다.
