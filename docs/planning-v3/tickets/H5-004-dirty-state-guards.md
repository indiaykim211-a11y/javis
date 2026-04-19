# H5-004 Dirty State Guards

## 목표

project / operations / prompt 편집 중에는 자동 sync가 local draft를 덮어쓰지 않도록 보호합니다.

## 완료 조건

- section dirty 계산
- dirty badge 또는 notice
- clean 상태면 자동 동기화
- dirty 상태면 local form 유지
