# javis Planning v3

## 목적

`planning-v3`는 `Python 엔진 + 웹 기술 데스크톱 셸` 방향으로 다시 짠 실행 문서 묶음입니다.

- 기존 `planning-v2`는 Tk 기반 제품 라인을 보존합니다.
- `planning-v3`는 `Electron + React`를 기본 셸로 보고, Python은 로컬 제어와 운영 엔진으로 유지합니다.
- 현재는 전체 뼈대와 `Phase 1` 실행 문서를 우선 상세화합니다.

## 읽는 순서

1. `hybrid-master-plan-v1.md`
2. `phases/phase-1-hybrid-foundation.md`
3. `releases/release-1-web-shell-alpha.md`
4. `tickets/H1-001-electron-react-shell-scaffold.md`
5. `tickets/H1-002-python-snapshot-api.md`
6. `tickets/H1-003-assistant-shell-ui.md`
7. `tickets/H1-004-dev-runbook-and-verification.md`
8. `phases/phase-2-assistant-surface-migration.md`
9. `releases/release-2-assistant-surface-beta.md`
10. `tickets/H2-001-surface-snapshot-contract.md`
11. `tickets/H2-002-web-assistant-layout.md`
12. `tickets/H2-003-deck-sections-and-signal-panels.md`
13. `tickets/H2-004-refresh-and-status-loop.md`
14. `tickets/H2-005-phase-2-verification.md`
15. `phases/phase-3-action-bridge.md`
16. `releases/release-3-action-bridge-beta.md`
17. `tickets/H3-001-action-api-contract.md`
18. `tickets/H3-002-python-bridge-actions.md`
19. `tickets/H3-003-background-auto-loop-bridge.md`
20. `tickets/H3-004-web-action-dock-wiring.md`
21. `tickets/H3-005-control-deck-drawer.md`
22. `tickets/H3-006-phase-3-verification.md`
23. `phases/phase-4-control-deck-workspace.md`
24. `releases/release-4-control-deck-workspace-beta.md`
25. `tickets/H4-001-control-deck-contract-and-endpoints.md`
26. `tickets/H4-002-project-plan-editor.md`
27. `tickets/H4-003-operations-editor-and-runbook.md`
28. `tickets/H4-004-prompt-workbench.md`
29. `tickets/H4-005-recent-project-reentry.md`
30. `tickets/H4-006-phase-4-verification.md`
31. `phases/phase-5-live-sync-workspace.md`
32. `releases/release-5-live-sync-beta.md`
33. `tickets/H5-001-workspace-bundle-contract.md`
34. `tickets/H5-002-activity-feed-api.md`
35. `tickets/H5-003-live-sync-heartbeat.md`
36. `tickets/H5-004-dirty-state-guards.md`
37. `tickets/H5-005-activity-timeline-ui.md`
38. `tickets/H5-006-phase-5-verification.md`
39. `phases/phase-6-intelligence-studio.md`
40. `releases/release-6-intelligence-studio-beta.md`
41. `tickets/H6-001-intelligence-contract-and-endpoint.md`
42. `tickets/H6-002-judgment-studio.md`
43. `tickets/H6-003-visual-studio.md`
44. `tickets/H6-004-voice-and-integration-studio.md`
45. `tickets/H6-005-intelligence-sync-guards.md`
46. `tickets/H6-006-phase-6-verification.md`

## 현재 방향 요약

- `겉`은 웹급 UI를 가진 데스크톱 셸입니다.
- `속`은 기존 Python 자동화/운영 엔진입니다.
- `Codex app`의 native 기능과 automations를 최대한 활용합니다.
- desktop macro는 주 경로가 아니라 fallback으로 남깁니다.

## 구현 원칙

- 현재 단계만 자세히 문서화합니다.
- 다음 단계는 중간 수준으로만 적고, 뒤 단계는 뼈대만 유지합니다.
- UI는 앞으로 `desktop-shell/`에서 진화시키고, Python Tk 앱은 운영 레퍼런스이자 기능 백엔드로 봅니다.

## 현재 상세화 상태

- `Phase 1`: 계획 + 구현 완료
- `Phase 2`: 계획 + 구현 완료
- `Phase 3`: 계획 + 구현 완료
- `Phase 4`: 계획 + 구현 완료
- `Phase 5`: 계획 + 구현 완료
- `Phase 6`: 계획 + 구현 완료
- `Phase 7 이후`: 큰 방향만 유지
