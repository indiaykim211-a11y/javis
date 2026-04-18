from __future__ import annotations

import json
from pathlib import Path

from app.models import SessionConfig


class SessionStore:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.runtime_dir = workspace / "runtime"
        self.capture_dir = workspace / "captures"
        self.session_path = self.runtime_dir / "session.json"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.capture_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> SessionConfig:
        if not self.session_path.exists():
            return SessionConfig()
        data = json.loads(self.session_path.read_text(encoding="utf-8"))
        return SessionConfig.from_dict(data)

    def save(self, session: SessionConfig) -> None:
        payload = json.dumps(session.to_dict(), ensure_ascii=False, indent=2)
        self.session_path.write_text(payload, encoding="utf-8")
