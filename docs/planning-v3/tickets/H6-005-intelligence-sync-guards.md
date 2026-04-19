# H6-005 Intelligence Sync Guards

## 목표

live sync가 켜져 있어도 intelligence draft 편집 상태를 안전하게 보존합니다.

## 완료 조건

- intelligence editor 변경 중에는 자동 새로고침이 draft를 덮어쓰지 않는다.
- 저장 후에는 최신 payload로 다시 동기화된다.
- dirty badge에 intelligence draft가 반영된다.
