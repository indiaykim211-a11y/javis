# javis

javis는 상단장님의 현재 작업 흐름을 대신해 주기 위한 Windows 데스크톱 앱 MVP입니다.

이 앱이 노리는 역할은 아래와 같습니다.

- Codex 앱 창을 찾고 포커스하기
- 작업이 멈춘 것처럼 보이는지 주기적으로 확인하기
- 다음 단계 프롬프트를 자동 또는 반자동으로 넣어 주기
- 화면 캡처와 로그를 남겨서 언제든 중간 확인하기

## 가능 여부

가능합니다. 다만 현실적으로는 두 층으로 나눠서 가는 게 가장 안전합니다.

- 1단계 MVP: Windows UI 자동화 + 화면 캡처 + 안정화 감지 + 다음 단계 전송
- 2단계 고도화: OCR 또는 비전 모델로 결과물 읽기 + 웹 페이지 검증 + 이상 시 자동 중단

현재 Codex 데스크톱 창은 프로세스/윈도우 단위로는 잘 잡히지만, 내부 텍스트가 UI Automation에 잘 드러나지 않을 가능성이 큽니다. 그래서 이번 MVP는 `창 상태를 읽고`, `스크린샷을 남기고`, `안정적으로 멈춘 시점에 다음 단계를 보내는 운영 앱`으로 출발합니다.

## 포함된 기능

- Codex 창 목록 조회
- Codex 창 포커스
- Codex 창 화면 캡처
- 입력창 상대 좌표 클릭
- 클립보드 붙여넣기로 다음 단계 전송
- 스크린샷 시그니처 기반 안정화 감지
- 자동 루프 실행 및 중지
- 세션 설정 저장

## 실행 방법

```powershell
python launcher.py
```

## 릴리즈 스모크

수동 체크리스트는 아래 문서를 보면 됩니다.

- `docs/planning-v2/checklists/release-1-smoke-checklist-v1.md`
- `docs/planning-v2/checklists/release-2-smoke-checklist-v1.md`
- `docs/planning-v2/checklists/release-3-smoke-checklist-v1.md`
- `docs/planning-v2/checklists/release-4-smoke-checklist-v1.md`
- `docs/planning-v2/checklists/release-5-smoke-checklist-v1.md`
- `docs/planning-v2/checklists/release-6-smoke-checklist-v1.md`

로컬 스모크 러너는 아래로 돌릴 수 있습니다.

```powershell
python scripts\release_1_smoke.py
python scripts\release_2_smoke.py
python scripts\release_3_smoke.py
python scripts\release_4_smoke.py
python scripts\release_5_smoke.py
python scripts\release_6_smoke.py
```

## 추천 사용 흐름

1. 앱을 실행합니다.
2. 프로젝트 요약, 목표, 단계 목록을 입력합니다.
3. Codex 입력창의 대략적인 상대 좌표를 넣습니다.
4. `창 새로고침`으로 Codex 창을 확인합니다.
5. `즉시 캡처`와 `다음 단계 보내기`를 먼저 수동으로 테스트합니다.
6. 이상이 없으면 `자동 루프 시작`으로 넘깁니다.

## 현재 한계

- Codex 내부 텍스트를 완전하게 읽는 기능은 아직 없습니다.
- 자동 완료 판단은 현재 `화면 안정화` 기반 휴리스틱입니다.
- 웹 결과물 자체를 합격/불합격 판정하는 비전 검수는 다음 단계입니다.

## 다음 구현 우선순위

1. Codex 스크린샷을 읽는 비전 판독기 추가
2. 브라우저 탭까지 같이 추적해서 결과 화면 검수
3. 실패 패턴 감지 시 재시도 또는 보정 프롬프트 전송
4. 작업 히스토리와 단계별 산출물 비교
