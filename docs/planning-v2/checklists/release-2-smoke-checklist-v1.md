# Release 2 Smoke Checklist v1

## 목적

Release 2 핵심 흐름인 `Codex 전략 선택 -> prompt 생성 -> 운영 프로필 저장/복원 -> 런북/매트릭스 확인`이 살아 있는지 5~10분 안에 점검합니다.

## 준비

- `python launcher.py` 실행
- Control Center 열기
- `Codex 전략` 섹션 진입

## 점검 시나리오

### 1. 전략 센터 기본 진입

- `Codex 전략` 섹션이 보임
- 전략 프리셋 콤보가 보임
- 추천 automation, cadence, worktree 안내가 보임

### 2. prompt 조합기

- 프로젝트 요약 / 목표 / 단계 입력
- 프리셋 선택 후 `프롬프트 새로고침`
- prompt 초안에 프로젝트 정보, 정책, 추가 지시가 반영됨
- `클립보드 복사` 동작 가능

### 3. 운영 프로필 저장/복원

- 전략 프리셋과 추가 지시 입력 후 저장
- 프로젝트 홈 카드에 현재 운영 프로필이 보임
- 최근 프로젝트 카드에도 운영 프로필이 보임
- 최근 프로젝트를 다시 불러왔을 때 같은 전략이 복원됨

### 4. 런북 / handoff

- 현재 프리셋 기준 handoff 순서가 표시됨
- thread / project automation 관련 안내가 보임
- `런북 복사` 동작 가능

### 5. Native vs Fallback

- 네이티브 우선 원칙이 표시됨
- fallback 조건과 pause 조건이 보임
- `매트릭스 복사` 동작 가능

## 빠른 자동 점검

아래 스크립트가 있으면 함께 실행합니다.

```powershell
python scripts\release_2_smoke.py
```

## 통과 기준

- 전략 선택, prompt 생성, 저장/복원, 런북, 매트릭스 흐름이 모두 살아 있음
- `Codex-first` 방향이 제품 안에서 눈에 보임
