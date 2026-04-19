# Codex Automations Playbook v1

## 문서 목적

이 문서는 `javis`가 Codex Automations를 어떻게 활용할지 정리한 운영 플레이북입니다.

핵심 목표는 간단합니다.

- Codex가 이미 해주는 반복 작업 기능을 최대한 활용하기
- `javis`는 그 위에서 감독과 통합에 집중하기

## 공식 문서 기준 핵심 사실

현재 공식 문서 기준으로 Automations는 아래처럼 이해하면 됩니다.

### 1. Automations는 반복 작업 스케줄러다

- 백그라운드에서 반복 작업을 돌립니다.
- 결과가 있으면 inbox / Triage에 올라옵니다.
- 특별히 보고할 것이 없으면 자동으로 아카이브될 수 있습니다.

### 2. thread automation이 있다

- 현재 대화 스레드에 붙는 heartbeat 스타일입니다.
- 같은 문맥을 유지하면서 다시 깨우는 데 적합합니다.
- 분 단위, 일 단위, 주 단위 스케줄을 쓸 수 있습니다.

### 3. standalone / project automation이 있다

- 매번 독립 실행처럼 새로 도는 방식입니다.
- 하나 이상의 프로젝트를 대상으로 반복 작업을 돌릴 수 있습니다.
- 필요하면 custom schedule과 cron 문법을 씁니다.

### 4. worktree를 같이 쓸 수 있다

- Git 저장소에서는 automation을 local project 또는 dedicated background worktree에서 돌릴 수 있습니다.
- unfinished local work와 automation 변경을 분리하고 싶으면 worktree가 더 안전합니다.

### 5. skills / plugins / rules와 같이 쓸 수 있다

- automations는 같은 skills와 plugins를 사용할 수 있습니다.
- 자주 반복되는 흐름은 skill로 묶어 두는 것이 유지보수에 좋습니다.

### 6. 프로젝트 자동화는 현재 제약이 있다

- project-scoped automation은 Codex 앱이 실행 중이어야 합니다.
- 선택한 프로젝트가 디스크에 있어야 합니다.

## javis 관점 핵심 해석

피디 해석으로는 Automations가 `javis의 적`이 아니라 `javis가 새로 만들 필요 없는 기반 기능`입니다.

즉:

- 반복 실행
- 정해진 주기 재확인
- 결과 inbox 수집
- review loop 재개

이 부분은 Codex 쪽을 먼저 믿고 가져갑니다.

## 언제 thread automation을 쓰는가

thread automation은 `같은 대화를 계속 이어가야 할 때` 씁니다.

### 추천 상황

- 같은 개발 스레드를 계속 추적할 때
- “조금 있다가 다시 보고 이어서 해”가 필요할 때
- 장기 review loop를 유지할 때
- PR 상태나 피드백을 같은 문맥에서 계속 보는 흐름

### javis에서 잘 맞는 활용

- 마스터플랜 진행 스레드 heartbeat
- 장기 디버깅 스레드 재확인
- “배포 끝날 때까지 10분마다 다시 봐” 같은 follow-up
- 상단장님이 잠깐 자리를 비울 때 같은 스레드 유지

### 장점

- 문맥이 이어집니다.
- 별도 요약 재구성이 덜 필요합니다.
- “이 대화 계속 이어가”에 가장 가깝습니다.

### 주의점

- 프롬프트를 durable하게 써야 합니다.
- 매번 깨어났을 때 무엇을 보고, 무엇을 보고하지 않고, 언제 멈출지 적어야 합니다.

## 언제 standalone / project automation을 쓰는가

standalone / project automation은 `매 실행을 독립적으로 보고 싶을 때` 씁니다.

### 추천 상황

- 매일 아침 프로젝트 브리핑
- nightly smoke test
- CI 실패 점검
- 일정 주기 repo 상태 체크
- 여러 프로젝트를 한 번에 도는 반복 점검

### javis에서 잘 맞는 활용

- 프로젝트별 진행 요약 자동 생성
- smoke suite 반복 실행
- recent bugfix / PR babysitting
- 특정 디렉터리 변경사항 exec brief

### 장점

- 실행 결과가 서로 덜 섞입니다.
- Triage에서 독립 run으로 보기 쉽습니다.
- 프로젝트가 여러 개여도 돌리기 좋습니다.

### 주의점

- 현재는 app이 켜져 있고, 프로젝트가 디스크에 있어야 하는 제약을 고려해야 합니다.
- local mode는 현재 작업 중인 파일을 직접 건드릴 수 있으므로 주의가 필요합니다.

## worktree 사용 원칙

피디 추천 기본값은 아래입니다.

### worktree를 기본으로 쓰는 경우

- 코드 변경이 생길 수 있는 automation
- 상단장님이 같은 저장소를 직접 편집 중인 경우
- 긴 주기로 계속 돌리는 자동화

### local project를 써도 되는 경우

- 읽기 위주 점검
- 변경이 거의 없는 요약 작업
- 현재 main checkout을 직접 다루는 것이 오히려 자연스러운 경우

## skill과 함께 쓸 때 좋은 점

Automations는 혼자 쓰는 것보다 skill과 함께 쓸 때 훨씬 강해집니다.

### 이유

- 자주 반복되는 운영 방식을 이름 붙여 재사용할 수 있음
- 팀 규칙과 툴 사용법을 한 번 묶어 둘 수 있음
- automation prompt가 너무 길어지는 것을 줄일 수 있음

### javis에서 특히 중요한 조합

- `PR babysitter` skill
- `release smoke` skill
- `recent-change brief` skill
- `codex-plan-followup` skill

## javis에 바로 맞는 활용 시나리오

### 1. 마스터플랜 follow-up heartbeat

종류:
- thread automation

목적:
- 같은 개발 스레드를 계속 다시 보고
- 다음 단계 진행 가능 여부를 체크
- 중요 변화가 있을 때만 알려주기

### 2. release smoke 자동 점검

종류:
- project automation

목적:
- `release_1_smoke.py` 같은 스크립트를 주기적으로 돌리고
- 실패 시 Triage에 올리기

### 3. PR babysitting

종류:
- thread automation 또는 project automation + skill

목적:
- PR 상태 보기
- 새 리뷰 코멘트 확인
- 필요 시 후속 수정 루프 이어가기

### 4. nightly project brief

종류:
- standalone / project automation

목적:
- 하루치 변경사항을 workstream 단위로 요약
- 상단장님이 아침에 빠르게 상황 파악

### 5. recent-code bugfix

종류:
- project automation + skill

목적:
- 최근 내 변경에서 생긴 문제를 미리 찾고 고치기

### 6. long-run babysit

종류:
- thread automation

목적:
- 배포, 테스트, 장기 명령, 외부 피드백 루프를 같은 스레드에서 계속 관찰

## automations가 대신할 수 있는 것

- 반복적인 재확인
- 일정 간격 follow-up
- smoke/brief/triage 같은 주기 작업
- 장기 스레드 깨우기
- PR / 리뷰 babysitting

## automations만으로는 부족한 것

이 부분은 여전히 `javis`가 더 잘해야 합니다.

- 데스크톱 팝업 UX
- 음성 입력 / 음성 응답
- Codex 화면 + 브라우저 화면을 함께 읽는 시각 감독
- 상단장님용 한국어 보고 경험
- Codex 결과, 화면 증거, 사용자 승인까지 합친 상위 판단

## 설계 결론

피디 추천 기본 전략은 아래입니다.

### 1. 먼저 Codex Automations로 해결 가능한지 본다

- 주기 실행인가
- 같은 문맥 유지가 중요한가
- 독립 실행이 좋은가
- skill로 묶을 수 있는가

### 2. 그다음 javis 감독 레이어를 붙인다

- 팝업 요약
- 정책 적용
- 사용자 보고
- 필요 시 재지시

### 3. 마지막에만 로컬 제어를 붙인다

- 화면 읽기
- 브라우저 감시
- 클릭 fallback

## 후속 작업 추천

- `codex-native-utilization-strategy-v1`에서 역할 분리 확정
- `automation-prompt-templates-v1.md`로 프롬프트 템플릿 구체화
- `javis-codex-automation-scenarios-v1.md`로 시나리오 상세화
- `project automation smoke suite` 상세화
