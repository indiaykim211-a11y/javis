from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.models import (
    PersistedSessionState,
    RecentProjectEntry,
    RuntimeState,
    SESSION_SCHEMA_VERSION,
    SessionConfig,
)


class SessionStore:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.runtime_dir = workspace / "runtime"
        self.capture_dir = workspace / "captures"
        self.session_path = self.runtime_dir / "session.json"
        self.log_path = self.runtime_dir / "javis.log"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.capture_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> PersistedSessionState:
        if not self.session_path.exists():
            return PersistedSessionState(log_path=str(self.log_path))
        data = json.loads(self.session_path.read_text(encoding="utf-8"))
        if self._is_legacy_session_payload(data):
            return PersistedSessionState(
                schema_version=SESSION_SCHEMA_VERSION,
                log_path=str(self.log_path),
                session=SessionConfig.from_dict(data),
                runtime=RuntimeState(),
            )

        persisted = PersistedSessionState.from_dict(data)
        if not persisted.log_path:
            persisted.log_path = str(self.log_path)
        return persisted

    def save(self, persisted: PersistedSessionState) -> PersistedSessionState:
        saved_at = datetime.now().isoformat(timespec="seconds")
        persisted.schema_version = SESSION_SCHEMA_VERSION
        persisted.saved_at = saved_at
        persisted.log_path = str(self.log_path)
        persisted.recent_projects = self._update_recent_projects(
            recent_projects=persisted.recent_projects,
            session=persisted.session,
            runtime=persisted.runtime,
            saved_at=saved_at,
        )
        payload = json.dumps(persisted.to_dict(), ensure_ascii=False, indent=2)
        self.session_path.write_text(payload, encoding="utf-8")
        return persisted

    def append_log(self, message: str) -> None:
        text = message.strip()
        if not text:
            return

        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = text.splitlines() or [text]
        with self.log_path.open("a", encoding="utf-8") as handle:
            for index, line in enumerate(lines):
                prefix = f"[{stamp}] " if index == 0 else " " * (len(stamp) + 3)
                handle.write(f"{prefix}{line}\n")

    def _is_legacy_session_payload(self, data: object) -> bool:
        if not isinstance(data, dict):
            return False
        return "schema_version" not in data and "project" in data and "window" in data

    def _update_recent_projects(
        self,
        *,
        recent_projects: list[RecentProjectEntry],
        session: SessionConfig,
        runtime: RuntimeState,
        saved_at: str,
    ) -> list[RecentProjectEntry]:
        project_key = self._project_key(session)
        if not project_key:
            return recent_projects[:5]

        entry = RecentProjectEntry(
            project_key=project_key,
            project_summary=session.project.project_summary,
            target_outcome=session.project.target_outcome,
            saved_at=saved_at,
            next_step_index=runtime.next_step_index,
            total_steps=len(session.project.steps()),
            last_capture_path=runtime.last_capture_path or "",
            session=SessionConfig.from_dict(session.to_dict()),
            runtime=RuntimeState.from_persisted_dict(runtime.to_persisted_dict()),
        )

        updated = [item for item in recent_projects if item.project_key != project_key]
        updated.insert(0, entry)
        return updated[:5]

    def _project_key(self, session: SessionConfig) -> str:
        parts = [
            session.project.project_summary.strip(),
            session.project.target_outcome.strip(),
            session.project.steps_text.strip(),
        ]
        return "\n".join(parts).strip()
