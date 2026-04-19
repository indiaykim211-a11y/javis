# Deep Integration Capability Matrix v1

## 목적

`Phase 7`에서 `javis`가 무엇을 사용할 수 있는지, 그리고 어떤 조건에서 어떤 integration mode를 추천할지 정리하는 기준 문서입니다.

## capability 축

### 1. Codex App Native

- 현재 로컬 app surface 사용 가능 여부
- thread / project automation 진입 가능 여부

### 2. App Server Readiness

- adapter 사용 가능
- handoff 대상 안정성
- 입력/출력 경계 명확성

### 3. Cloud Trigger Readiness

- background follow-up 성숙도
- 재진입 가능성
- review / triage와의 연결성

### 4. Desktop Fallback Need

- native로 충분한가
- native가 막혔는가
- fallback이 정말 필요한가

## integration mode 분류

### Mode A. Native App Assisted

- 기본 추천
- thread / project / triage 중심

### Mode B. App Server Assisted

- App Server readiness가 충분할 때만
- 공식 표면 우선

### Mode C. Cloud-Triggered Supervision

- cloud follow-up 성숙 시 고려
- `javis`는 watch / re-entry에 집중

### Mode D. Desktop Fallback

- native가 비어 있거나 부족할 때만
- 사용 이유를 반드시 남김

## 추천 원칙

- 같은 결과를 native로 얻을 수 있으면 native를 먼저
- readiness가 불명확하면 더 보수적인 mode를 추천
- fallback은 `예외`이지 `기본`이 아님

## 출력 예시

- recommended_mode
- selected_mode
- capability_summary
- readiness_notes
- fallback_reason
- next_review_point
