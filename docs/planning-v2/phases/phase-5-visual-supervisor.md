# Phase 5: Visual Supervisor

## 단계 목적

이 단계의 목적은 `javis`가 `Codex-first 실행 + Judgment Overlay` 위에 `시각 증거 감독층`을 얹는 것입니다.

핵심은 아래 한 줄입니다.

`텍스트와 네이티브 결과만으로 확신이 부족할 때, javis가 화면을 읽어 판단 근거를 강화한다.`

## 왜 이 단계가 필요한가

Phase 4까지 오면 `javis`는 아래를 꽤 잘하게 됩니다.

- Codex 운영 모드를 고르고
- 결과를 구조화 판단으로 바꾸고
- continue / retry / pause / ask_user를 분기하고
- 위험한 경우 자동 진행을 멈추고
- 상단장님께 짧고 명확하게 설명

하지만 아직 아래는 약합니다.

- Codex가 `됐습니다`라고 말했는데 실제 화면도 정말 그런지
- 브라우저 결과가 실제로 정상인지
- 버튼/폼/페이지가 눈으로 봤을 때도 의도대로 보이는지
- 오류 배너, 빈 화면, 잘못된 라우팅, UI 깨짐 같은 시각 이상 신호가 있는지

즉 Phase 5는 `판단의 눈`을 붙이는 단계입니다.

## 이 단계의 기본 철학

### 1. 화면 인식은 네이티브 우선 전략을 깨지 않는다

Phase 5는 `무조건 모든 화면을 OCR/비전으로 읽는 단계`가 아닙니다.

- 먼저 Codex 네이티브 결과
- 그다음 로그 / runboard / triage / 현재 단계 문맥
- 그래도 부족하거나 모순이 보일 때만 화면 증거

즉 시각 입력은 `항상 기본`이 아니라 `필요할 때만 켜는 근거 강화층`입니다.

### 2. 화면 인식의 목표는 설명이 아니라 판정 보조다

이 단계의 본질은 화면을 멋지게 설명하는 것이 아닙니다.

- 지금 상태가 정상인지
- Codex 주장과 화면이 일치하는지
- retry가 필요한지
- 상단장님 호출이 필요한지

이 판정에 필요한 만큼만 읽어야 합니다.

### 3. 전체 화면보다 타깃 캡처가 먼저다

비전 입력이 무한정 커지면 비용과 노이즈가 같이 커집니다.

그래서 Phase 5에서는 아래를 우선합니다.

- Codex 창
- 브라우저 결과 화면
- 특정 오류 영역
- 필요한 경우만 부분 캡처 / 비교 캡처

### 4. 시각 증거는 판단 오버레이에 합쳐진다

Phase 5는 새 판단 엔진을 만드는 단계가 아닙니다.

- Phase 4의 판단 엔진이 중심
- Phase 5는 그 엔진에 시각 evidence를 추가

즉 `Visual Supervisor`는 `Judgment Overlay`의 입력 강화판입니다.

## 이 단계에서 javis가 맡을 것

### 1. Capture Target Planner

지금 무엇을 캡처해야 가장 적은 비용으로 가장 좋은 근거를 얻는지 결정합니다.

### 2. Visual Evidence Packet

캡처 대상, 관찰 포인트, 현재 단계 문맥, 최근 Codex 주장, 기대 화면을 묶어 시각 판단 입력으로 만듭니다.

### 3. Browser / Codex Observation Prompt

Codex 창, 브라우저 결과, 오류 배너, 주요 CTA, 페이지 상태 같은 포인트를 짧게 읽게 하는 관찰 프롬프트를 만듭니다.

### 4. Claim vs Screen Contradiction Detection

Codex가 말한 완료 상태와 실제 화면이 다르면 그 모순을 강하게 표시합니다.

### 5. Visual Summary Surface

팝업과 Control Center에서 아래가 짧게 보여야 합니다.

- 무엇을 봤는지
- 실제 화면이 어땠는지
- Codex 주장과 일치하는지
- 다음 행동이 무엇인지

### 6. Visual Rejudge Bridge

시각 증거를 Phase 4 판단 루프에 다시 넣어 `continue / retry / ask_user`를 재판정합니다.

### 7. Privacy / Capture Guard

쓸데없이 많은 화면을 저장하거나 민감한 내용을 오래 남기지 않도록 가드를 둡니다.

## 이 단계에서 javis가 직접 하지 않을 것

- 무조건 모든 화면을 OCR로 돌리기
- 브라우저 테스트 러너 전체 재구현
- 음성 입력 / 음성 응답
- Codex 앱 실행 엔진 대체
- App Server 직접 통합

## 이 단계에서 Codex가 맡는 것

- 여전히 코드 작성 / 수정 / 실행 / automation
- 같은 스레드 또는 project automation 결과 생성
- worktree / triage / runboard / launch prompt 기반 진행

## 이 단계에서 OpenAI 비전 / 판단 계층이 맡는 것

- 특정 캡처의 핵심 상태 요약
- Codex 주장과 실제 화면의 일치 여부 판정
- 오류 배너 / 빈 화면 / CTA 부재 / 잘못된 라우팅 / UI 깨짐 감지
- 시각 증거를 포함한 재판단

## 핵심 사용자 시나리오

### 시나리오 A. Codex는 완료라고 했지만 브라우저가 비어 있음

- Codex 결과는 `done`
- 브라우저 캡처는 빈 화면 또는 에러 배너
- `javis`는 continue 대신 retry 또는 ask_user

### 시나리오 B. Codex 창에는 성공처럼 보이지만 실제 버튼이 없음

- Codex 응답은 낙관적
- 실제 UI에서 핵심 CTA가 사라짐
- `javis`는 claim vs screen mismatch로 판단

### 시나리오 C. project automation 결과를 다시 볼 때

- Triage에 smoke 결과가 올라옴
- 필요한 브라우저 캡처만 추가로 읽음
- 시각 근거를 붙여 최종 판단

### 시나리오 D. 애매한 시각 신호

- 화면 인식 확신이 낮음
- 텍스트 근거도 충분하지 않음
- `javis`는 억지 continue 대신 ask_user 또는 pause

## 완료 조건

- 시각 evidence가 언제 필요한지 제품 안에서 명확해짐
- Codex 주장과 실제 화면의 모순을 탐지할 수 있음
- 판단 엔진이 visual evidence를 입력으로 다시 받을 수 있음
- 팝업과 Control Center에서 `왜 retry인지 / 왜 ask_user인지`가 더 설득력 있게 보임
- Release 6에서 음성과 시각 요약이 같은 판단 엔진을 공유할 준비가 됨

## 다음 연결 문서

- `../releases/release-5-visual-beta.md`
- `../specs/visual-evidence-contract-v1.md`
- `../ai/openai-judgment-engine-v1.md`
