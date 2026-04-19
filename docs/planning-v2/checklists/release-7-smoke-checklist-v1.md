# Release 7 Smoke Checklist v1

## 목적

`Release 7`의 deep integration 문서와 운영 원칙이 실제로 일관되게 읽히는지 빠르게 점검합니다.

## 1. Capability Registry

- 현재 환경 capability를 적을 수 있다
- App Server / cloud trigger / native / fallback 경계가 보인다

## 2. Integration Mode Broker

- recommended mode와 selected mode를 구분해 설명할 수 있다
- 왜 그 mode가 맞는지 근거가 있다

## 3. Cross-Surface Handoff

- popup / Control Center / voice / triage를 오갈 때 문맥이 끊기지 않는다
- handoff bundle의 최소 정보가 정의돼 있다

## 4. Supervisor State

- 현재 watch / waiting / re-enter / escalate / fallback 상태를 설명할 수 있다

## 5. Fallback Boundary

- native 경로가 충분하면 fallback을 쓰지 않는 이유가 분명하다
- fallback으로 내려간 경우 이유와 종료 조건이 있다

## 6. 운영 보고

- 상단장님께 현재 deep integration 상태를 한 줄로 요약할 수 있다
- 현재 리스크와 다음 검토 시점이 있다
