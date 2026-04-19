# H5-003 Live Sync Heartbeat

## 목표

web shell이 workspace bundle을 주기적으로 읽어 snapshot과 control deck를 함께 갱신합니다.

## 완료 조건

- mount 시 최초 load
- interval heartbeat
- manual refresh
- deck open 상태와 함께 동작
