from __future__ import annotations

import shutil
import sys
from pathlib import Path
from tkinter import END, Tk

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models import JudgmentResult, RuntimeState
from app.ui import JavisApp


class SmokeFailure(RuntimeError):
    pass


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def set_text(widget, text: str) -> None:
    widget.delete("1.0", END)
    widget.insert("1.0", text)
    try:
        widget.edit_modified(True)
    except Exception:
        pass


def print_step(title: str, detail: str) -> None:
    print(f"[PASS] {title}: {detail}")


def seed_phase_8_project(app: JavisApp) -> None:
    set_text(app.project_summary, "Release 8 Smoke")
    set_text(app.target_outcome, "Codex 운영을 live ops lane과 re-entry 기준으로 굴린다")
    set_text(
        app.steps_text,
        "\n".join(
            [
                "현재 lane을 판단한다",
                "Codex launch와 re-entry 규칙을 정리한다",
                "막히면 recovery playbook으로 복구한다",
            ]
        ),
    )
    app.root.update_idletasks()


def prime_runtime(app: JavisApp, workspace: Path) -> None:
    capture_dir = workspace / "captures"
    capture_dir.mkdir(parents=True, exist_ok=True)
    capture_path = capture_dir / "phase8-smoke.bmp"
    capture_path.write_bytes(b"BM")

    app.runtime = RuntimeState()
    app.runtime.next_step_index = 0
    app.runtime.auto_running = False
    app.runtime.clear_operator_pause()
    app.runtime.last_target_title = "Codex"
    app.runtime.last_target_reason = "phase 8 smoke target is ready"
    app.runtime.last_target_score = 99
    app.runtime.target_lock_status = "locked"
    app.runtime.stable_cycles = 5
    app.runtime.last_capture_path = str(capture_path.resolve())


def main() -> None:
    workspace = Path("runtime/release-8-smoke-suite")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    root = Tk()
    app = JavisApp(root, workspace)

    try:
        root.update_idletasks()
        app.open_control_center()
        app._select_control_center_section("codex_strategy")
        root.update_idletasks()

        ensure(app.control_section_var.get() == "codex_strategy", "Codex 전략 섹션으로 이동하지 못했습니다.")
        ensure(app.live_ops_profile_var.get().strip(), "Live Operations profile 필드가 비어 있습니다.")
        print_step("live ops section", "Codex 전략 섹션 안에 Live Operations 패널이 보입니다.")

        seed_phase_8_project(app)
        prime_runtime(app, workspace)
        app.refresh_prompt_preview()
        root.update_idletasks()

        ensure("launch_ready" in app.live_ops_lane_status_var.get(), "기본 lane이 launch_ready로 잡히지 않았습니다.")
        ensure(app._current_live_ops_charter.strip(), "operations charter가 생성되지 않았습니다.")
        ensure(app._current_live_ops_launchpad.strip(), "launchpad가 생성되지 않았습니다.")
        print_step("launch ready", "기본 운영 상태에서 launch_ready lane과 charter / launchpad가 생성됩니다.")

        app.live_ops_profile_var.set(app._live_ops_profile_label_for_id("hands_off"))
        app.live_ops_report_var.set(app._live_ops_report_label_for_id("risk_only"))
        app.live_ops_reentry_var.set(app._live_ops_reentry_label_for_id("triage_first"))
        app.live_ops_max_steps_var.set("5")
        set_text(app.live_ops_note, "Prefer triage-first re-entry during unattended runs.")
        app.refresh_live_ops_panel_now()
        root.update_idletasks()
        ensure("자율 운용" in app.live_ops_profile_status_var.get(), "live ops profile 변경이 반영되지 않았습니다.")
        ensure("Triage / Automations" in app._current_live_ops_reentry_brief, "triage-first re-entry brief가 생성되지 않았습니다.")
        print_step("profile override", "자율 운용 / 위험 신호만 / triage-first 운영 프로필이 반영됩니다.")

        app.runtime.auto_running = True
        app._refresh_live_ops_panel(app._collect_session())
        root.update_idletasks()
        ensure("active_run" in app.live_ops_lane_status_var.get(), "auto_running 상태에서 active_run lane이 보이지 않습니다.")
        print_step("active run", "자동 루프가 돌면 active_run lane으로 전환됩니다.")

        app.runtime.auto_running = False
        app.runtime.set_operator_pause("Need manual approval")
        app._refresh_live_ops_panel(app._collect_session())
        root.update_idletasks()
        ensure("blocked" in app.live_ops_lane_status_var.get(), "operator pause 상태에서 blocked lane이 보이지 않습니다.")
        ensure("manual" in app.live_ops_recovery_status_var.get(), "blocked 상태에서 recovery level이 manual로 올라가지 않았습니다.")
        print_step("blocked recovery", "operator pause가 있으면 blocked lane과 manual recovery를 보여줍니다.")

        app.runtime.clear_operator_pause()
        app.codex_mode_var.set(app._codex_mode_label_for_id("project_automation"))
        app.runtime.last_judgment = JudgmentResult(
            decision="continue",
            reason="Automation result is ready",
            confidence=0.88,
            risk_level="low",
            message_to_user="Triage 결과를 읽고 재진입할 준비가 됐습니다.",
            evaluated_at="2026-04-19T21:00:00",
            source="release_8_smoke",
        )
        app._refresh_live_ops_panel(app._collect_session())
        root.update_idletasks()
        ensure("reentry_ready" in app.live_ops_lane_status_var.get(), "project automation 결과 후 reentry_ready lane이 보이지 않습니다.")
        ensure("Triage / Automations" in app._current_live_ops_reentry_brief, "re-entry brief가 triage-first 흐름을 반영하지 않았습니다.")
        print_step("re-entry ready", "automation 결과가 있으면 reentry_ready lane과 re-entry brief가 갱신됩니다.")

        app.save_session()
        root.update_idletasks()

        restored_root = Tk()
        restored_app = JavisApp(restored_root, workspace)
        try:
            restored_root.update_idletasks()
            restored_app.open_control_center()
            restored_app._select_control_center_section("codex_strategy")
            restored_root.update_idletasks()

            ensure(
                restored_app.live_ops_profile_var.get() == restored_app._live_ops_profile_label_for_id("hands_off"),
                "재실행 후 live ops profile이 유지되지 않았습니다.",
            )
            ensure(
                restored_app.live_ops_report_var.get() == restored_app._live_ops_report_label_for_id("risk_only"),
                "재실행 후 live ops cadence가 유지되지 않았습니다.",
            )
            ensure(
                restored_app.live_ops_reentry_var.get() == restored_app._live_ops_reentry_label_for_id("triage_first"),
                "재실행 후 live ops re-entry mode가 유지되지 않았습니다.",
            )
            ensure(
                restored_app.live_ops_max_steps_var.get() == "5",
                "재실행 후 max unattended steps가 유지되지 않았습니다.",
            )
            ensure(
                "Prefer triage-first re-entry" in restored_app.live_ops_note.get("1.0", END),
                "재실행 후 operator note가 유지되지 않았습니다.",
            )
            ensure(
                "라이브 운영:" in restored_app.project_home_strategy_var.get(),
                "project home에 live ops 요약이 반영되지 않았습니다.",
            )
            print_step("live ops persistence", "live ops 설정과 메모가 세션 복원 후에도 유지됩니다.")
        finally:
            try:
                restored_app.control_center.destroy()
            except Exception:
                pass
            restored_root.destroy()

        print("")
        print("[DONE] Release 8 smoke suite passed")
        print(f"[INFO] workspace={workspace.resolve()}")
        print(f"[INFO] session={app.store.session_path.resolve()}")
        print(f"[INFO] log={app.store.log_path.resolve()}")
    finally:
        try:
            app.control_center.destroy()
        except Exception:
            pass
        root.destroy()


if __name__ == "__main__":
    try:
        main()
    except SmokeFailure as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1) from exc
