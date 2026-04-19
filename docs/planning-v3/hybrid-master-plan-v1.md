# javis Hybrid Master Plan v1

## 0. 한 줄 정의

`javis`는 `Codex를 가장 잘 쓰게 만드는 데스크톱 어시스턴트`이며, 제품 구조는 `Python 운영 엔진 + Electron/React UI 셸`을 기본으로 합니다.

## 1. 왜 방향을 바꾸는가

기존 Tk 기반 앱은 기능 검증과 운영 로직 실험에는 아주 좋았습니다.
하지만 상단장님이 원하는 수준의 `세련된 자비스 비주얼`과 `웹급 UI 완성도`를 계속 끌어올리려면 셸을 웹 기술로 바꾸는 편이 훨씬 유리합니다.

그래서 방향을 이렇게 고정합니다.

- 로컬 제어, 상태 저장, 운영 엔진, desktop fallback: `Python`
- 실제 사용자 표면, 디자인 시스템, 고급 상호작용: `Electron + React`
- 장기적으로 더 직접적인 Codex 연결이 열리면: `native/App Server/cloud 경로 우선`

## 2. 제품 구조

### 2-1. Python Engine Layer

- 세션 저장/복원
- 운영 정책
- Codex 제어 엔진
- 화면/시각/음성 판단 파이프라인
- desktop fallback
- 로컬 API 서버

### 2-2. Web Shell Layer

- Assistant Surface
- Control Deck
- Live Operations HUD
- 상태 카드, 타임라인, 액션 도크
- 고급 디자인 시스템과 인터랙션

### 2-3. Integration Layer

- Electron preload / IPC
- Python local API bridge
- 향후 App Server / cloud trigger / automation handoff

## 3. 우선순위

1. Codex app을 더 잘 쓰게 만드는 운영 능력
2. 세련된 데스크톱 어시스턴트 표면
3. 화면 인식과 판단 증거
4. 음성 입력/브리핑
5. deep integration과 live ops

## 4. 단계 구조

### Phase 1. Hybrid Foundation

목표:
- Electron + React 셸을 세운다.
- Python 상태를 웹 셸이 읽을 수 있게 한다.
- 기존 Tk 앱을 당장 버리지 않고 병행 가능한 상태로 둔다.

완료 기준:
- `desktop-shell/`이 생기고 dev/build 구조가 잡혀 있다.
- Python local snapshot API가 동작한다.
- 웹 셸이 실제 세션 상태를 읽어 카드 UI로 보여준다.

### Phase 2. Assistant Surface Migration

목표:
- 현재 Tk 팝업의 핵심 경험을 React 셸로 옮긴다.
- Assistant Surface를 제품 중심 화면으로 만든다.

### Phase 3. Control Deck Migration

목표:
- 프로젝트 홈, 정책, Codex 전략, 판단, 시각, 음성 패널을 웹 Control Deck으로 옮긴다.

### Phase 4. Engine Bridge Expansion

목표:
- 읽기 전용 snapshot을 넘어서 액션 호출까지 연결한다.
- pause/resume/rejudge/brief 같은 제어를 web shell에서 보낸다.

### Phase 5. Codex-First Live Ops

목표:
- Codex automations, triage, handoff, re-entry 흐름을 web shell 중심으로 다룬다.

### Phase 6. Intelligence Studio

목표:
- 판단, 시각, 음성, Deep Integration 설정을 web shell 안에서 함께 다룬다.
- 기존 Python 운영 두뇌를 `Intelligence Studio` 형태로 노출한다.

### Phase 7. Deep Integration

목표:
- App Server, cloud trigger, desktop fallback boundary를 더 정교하게 관리한다.

## 5. 기술 원칙

- 셸은 웹처럼 만들고, 엔진은 Python으로 유지합니다.
- 브라우저 같은 디자인 자유도는 React/CSS에서 해결합니다.
- 시스템 제어와 Codex 연동 fallback은 Python에 남깁니다.
- 기능을 두 번 만들지 않고, 먼저 엔진을 분리한 뒤 UI를 바꿉니다.

## 6. 지금 바로 실행할 범위

지금은 `Phase 1`만 상세하게 진행합니다.

- H1-001: Electron + React 셸 스캐폴드
- H1-002: Python snapshot API
- H1-003: 자비스 스타일 Assistant Surface
- H1-004: 실행/검증 런북

다음 상세화는 `Phase 2` 진입 직전에 다시 합니다.
