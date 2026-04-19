# Release 6 Smoke Checklist v1

## 목적

Release 6 voice 흐름을 5~10분 안에 반복 점검하기 위한 기준 체크리스트입니다.

## 핵심 시나리오

### 시나리오 1. push-to-talk 진입

- voice capture 시작이 보인다
- 종료 후 transcript가 남는다

### 시나리오 2. 진행 명령

- `다음 단계 진행해`가 continue intent로 정규화된다
- 안전하면 기존 action router로 이어진다

### 시나리오 3. 상태 요약

- 현재 상태 요약을 음성 briefing으로 읽어준다

### 시나리오 4. 왜 멈췄어

- pause reason / last judgment / visual mismatch 중 필요한 내용을 읽어준다

### 시나리오 5. 위험 명령 confirmation

- 위험 명령은 바로 실행되지 않는다
- 확인 질문 또는 보류 흐름이 보인다

### 시나리오 6. 설정 / 장치 복원

- voice 설정이 저장된다
- 재실행 후 복원된다
