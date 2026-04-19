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
            persisted = PersistedSessionState(
                schema_version=SESSION_SCHEMA_VERSION,
                log_path=str(self.log_path),
                session=SessionConfig.from_dict(data),
                runtime=RuntimeState(),
            )
        else:
            persisted = PersistedSessionState.from_dict(data)
            if not persisted.log_path:
                persisted.log_path = str(self.log_path)
        if self._sanitize_persisted_state(persisted):
            self._write_snapshot(persisted)
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

    def _write_snapshot(self, persisted: PersistedSessionState) -> None:
        payload = json.dumps(persisted.to_dict(), ensure_ascii=False, indent=2)
        self.session_path.write_text(payload, encoding="utf-8")

    def _sanitize_persisted_state(self, persisted: PersistedSessionState) -> bool:
        changed = False
        if self._sanitize_session_config(persisted.session):
            changed = True
        if self._sanitize_runtime_state(persisted.runtime):
            changed = True

        sanitized_recent_projects: list[RecentProjectEntry] = []
        for entry in persisted.recent_projects:
            if self._sanitize_recent_project(entry):
                changed = True
            if entry.project_key.strip():
                sanitized_recent_projects.append(entry)
            else:
                changed = True
        if len(sanitized_recent_projects) != len(persisted.recent_projects):
            changed = True
        persisted.recent_projects = sanitized_recent_projects
        return changed

    def _sanitize_session_config(self, session: SessionConfig) -> bool:
        changed = False

        cleaned_summary = self._sanitize_text_field(session.project.project_summary)
        if cleaned_summary != session.project.project_summary:
            session.project.project_summary = cleaned_summary
            changed = True

        cleaned_target = self._sanitize_text_field(session.project.target_outcome)
        if cleaned_target != session.project.target_outcome:
            session.project.target_outcome = cleaned_target
            changed = True

        cleaned_steps = self._sanitize_multiline_field(session.project.steps_text)
        if cleaned_steps != session.project.steps_text:
            session.project.steps_text = cleaned_steps
            changed = True

        return changed

    def _sanitize_runtime_state(self, runtime: RuntimeState) -> bool:
        changed = False
        if self._looks_corrupted_text(runtime.prompt_generated) or self._looks_corrupted_text(runtime.prompt_draft):
            runtime.clear_prompt_preview()
            changed = True
        return changed

    def _sanitize_recent_project(self, entry: RecentProjectEntry) -> bool:
        changed = False
        if self._sanitize_session_config(entry.session):
            changed = True
        if self._sanitize_runtime_state(entry.runtime):
            changed = True

        cleaned_summary = self._sanitize_text_field(entry.project_summary)
        if cleaned_summary != entry.project_summary:
            entry.project_summary = cleaned_summary
            changed = True

        cleaned_target = self._sanitize_text_field(entry.target_outcome)
        if cleaned_target != entry.target_outcome:
            entry.target_outcome = cleaned_target
            changed = True

        parts = [
            entry.session.project.project_summary.strip(),
            entry.session.project.target_outcome.strip(),
            entry.session.project.steps_text.strip(),
        ]
        cleaned_project_key = "\n".join(part for part in parts if part).strip()
        if cleaned_project_key != entry.project_key:
            entry.project_key = cleaned_project_key
            changed = True
        if not entry.project_summary:
            entry.project_summary = entry.session.project.project_summary
        if not entry.target_outcome:
            entry.target_outcome = entry.session.project.target_outcome
        return changed

    def _sanitize_text_field(self, text: str) -> str:
        value = text.strip()
        if not value:
            return ""
        return "" if self._looks_corrupted_text(value) else text

    def _sanitize_multiline_field(self, text: str) -> str:
        if not text.strip():
            return ""
        cleaned_lines = [line for line in text.splitlines() if not self._looks_corrupted_text(line.strip())]
        return "\n".join(cleaned_lines).strip()

    def _looks_corrupted_text(self, text: str) -> bool:
        if not text:
            return False
        if "\ufffd" in text or "???" in text:
            return True
        stripped = text.strip()
        if not stripped or "?" not in stripped:
            return False
        question_count = stripped.count("?")
        meaningful_count = sum(1 for char in stripped if char not in {"?", " ", "\t", "\n", "\r", "-", "_", "|", "/", ":", "."})
        return question_count >= 2 and question_count >= meaningful_count

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
