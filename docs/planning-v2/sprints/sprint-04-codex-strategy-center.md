# Sprint 4: Codex Strategy Center

## 스프린트 목표

`javis` 안에서 현재 프로젝트에 맞는 Codex 운영 전략을 바로 고르고, prompt 초안까지 확인할 수 있게 만듭니다.

## 왜 먼저 하는가

Phase 2의 핵심은 기능 추가보다 `Codex-first 운영 기준을 제품 표면으로 끌어올리는 것`입니다. 그러려면 가장 먼저 `전략 선택 화면`이 보여야 합니다.

## 포함 티켓

- `R2-001` Codex 전략 센터
- `R2-002` Prompt 템플릿 조합기

## 상세 목표

### 1) 전략 선택 경험 만들기

- 상위 시나리오 프리셋 선택
- thread / project automation 추천 표시
- worktree 권장 여부와 cadence 안내

### 2) 현재 프로젝트와 연결

- 단순 문서 링크가 아니라 현재 프로젝트 요약, 목표, 단계와 결합된 prompt 초안 보여주기

### 3) Release 3 연결 준비

- 지금은 자동 생성까지 안 가더라도, 이후 automations 생성 흐름으로 이어질 데이터 구조 확보

## 완료 조건

- 전략 센터에서 현재 프로젝트에 맞는 Codex 운영 프리셋을 고를 수 있음
- prompt 초안을 앱 안에서 확인하고 복사할 수 있음
- Control Center 안에서 `Codex 네이티브 운영`의 자리가 생김

## 데모 시나리오

1. javis 실행
2. Control Center에서 `Codex 전략` 탭 진입
3. `마스터플랜 Follow-up` 프리셋 선택
4. 현재 프로젝트 기준 prompt 초안 확인
5. 클립보드 복사 또는 Codex 제어 섹션 이동

## 주요 리스크

- 전략 문구가 너무 길어지면 사용성이 떨어질 수 있음
- 프로젝트 정보가 부족할 때 prompt 초안이 비어 보일 수 있음
- 전략 센터가 문서 뷰어처럼 느껴질 수 있음

## 스프린트 산출물

- Codex Strategy Center v1
- Prompt Composer v1
