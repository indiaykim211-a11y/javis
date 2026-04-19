from __future__ import annotations

import shutil
import sys
from pathlib import Path
from tkinter import END, Tk

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models import RuntimeState
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


def seed_phase_7_project(app: JavisApp) -> None:
    set_text(app.project_summary, "Release 7 Smoke")
    set_text(app.target_outcome, "Codex native, App Server, cloud trigger, desktop fallback 경계를 점검한다")
    set_text(
        app.steps_text,
        "\n".join(
            [
                "현재 integration readiness를 점검한다",
                "handoff bundle과 observability 보고를 준비한다",
                "필요하면 fallback 경계를 다시 조정한다",
            ]
        ),
    )
    app.root.update_idletasks()


def prime_runtime(app: JavisApp, workspace: Path) -> None:
    capture_dir = workspace / "captures"
    capture_dir.mkdir(parents=True, exist_ok=True)
    capture_path = capture_dir / "phase7-smoke.bmp"
    capture_path.write_bytes(b"BM")

    app.runtime = RuntimeState()
    app.runtime.next_step_index = 1
    app.runtime.auto_running = False
    app.runtime.clear_operator_pause()
    app.runtime.last_target_title = "Codex"
    app.runtime.last_target_reason = "phase 7 smoke target is ready"
    app.runtime.last_target_score = 97
    app.runtime.target_lock_status = "locked"
    app.runtime.stable_cycles = 4
    app.runtime.last_capture_path = str(capture_path.resolve())


def main() -> None:
    workspace = Path("runtime/release-7-smoke-suite")
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
        ensure(app.deep_integration_mode_var.get().strip(), "Deep Integration mode 필드가 비어 있습니다.")
        print_step("deep integration section", "Phase 7 Control Center 섹션과 Deep Integration 필드가 보입니다.")

        seed_phase_7_project(app)
        prime_runtime(app, workspace)
        app.refresh_prompt_preview()
        root.update_idletasks()

        ensure(app._current_deep_integration_registry.strip(), "capability registry가 생성되지 않았습니다.")
        ensure("native app assisted" in app.deep_integration_mode_status_var.get(), "기본 추천 mode가 native app assisted가 아닙니다.")
        print_step("default recommendation", "기본 readiness에서는 native app assisted 경로를 추천합니다.")

        app.deep_app_server_readiness_var.set(app._deep_integration_readiness_label_for_id("ready"))
        app.deep_app_server_notes_var.set("App Server handoff is available.")
        app._on_deep_integration_settings_changed()
        root.update_idletasks()
        ensure("App Server assisted" in app.deep_integration_mode_status_var.get(), "App Server readiness가 ready일 때 mode가 바뀌지 않았습니다.")
        print_step("app server recommendation", "App Server readiness를 ready로 두면 assisted mode로 전환됩니다.")

        app.deep_app_server_readiness_var.set(app._deep_integration_readiness_label_for_id("unavailable"))
        app.deep_cloud_trigger_readiness_var.set(app._deep_integration_readiness_label_for_id("ready"))
        app.deep_cloud_trigger_notes_var.set("Cloud follow-up is available.")
        app._on_deep_integration_settings_changed()
        root.update_idletasks()
        ensure(
            "cloud trigger supervision" in app.deep_integration_mode_status_var.get(),
            "Cloud trigger readiness가 ready일 때 supervision mode가 보이지 않습니다.",
        )
        print_step("cloud trigger recommendation", "Cloud readiness를 ready로 두면 supervision 경로를 추천합니다.")

        app.deep_cloud_trigger_readiness_var.set(app._deep_integration_readiness_label_for_id("unavailable"))
        app.deep_integration_mode_var.set(app._deep_integration_mode_label_for_id("desktop_fallback"))
        app.deep_fallback_allowed_var.set(False)
        app._on_deep_integration_settings_changed()
        root.update_idletasks()
        ensure("blocked" in app.deep_integration_fallback_var.get(), "desktop fallback 차단 상태가 표시되지 않았습니다.")
        print_step("fallback boundary", "desktop fallback 허용을 끄면 blocked 상태로 경계를 고정합니다.")

        app.runtime.set_operator_pause("Need manual approval")
        app._refresh_deep_integration_panel(app._collect_session())
        root.update_idletasks()
        ensure("escalate" in app.deep_integration_supervisor_var.get(), "operator pause 상태에서 supervisor가 escalate로 바뀌지 않았습니다.")
        print_step("supervisor escalate", "operator pause가 있으면 supervisor state를 escalate로 올립니다.")

        app.runtime.clear_operator_pause()
        app.deep_integration_mode_var.set(app._deep_integration_mode_label_for_id("app_server_assisted"))
        app.deep_app_server_readiness_var.set(app._deep_integration_readiness_label_for_id("ready"))
        app.deep_cloud_trigger_readiness_var.set(app._deep_integration_readiness_label_for_id("unavailable"))
        app.deep_fallback_allowed_var.set(True)
        app.deep_app_server_notes_var.set("App Server handoff is available.")
        app.deep_cloud_trigger_notes_var.set("Cloud trigger is parked for later.")
        set_text(app.deep_handoff_note, "Prefer App Server handoff when native launch is not enough.")
        app.refresh_deep_integration_panel_now()
        root.update_idletasks()
        ensure(
            "Deep integration:" in app.project_home_strategy_var.get(),
            "프로젝트 홈 전략 카드에 deep integration 요약이 반영되지 않았습니다.",
        )
        print_step("project home summary", "프로젝트 홈 카드에 Deep Integration 요약이 함께 표시됩니다.")

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
                restored_app.deep_integration_mode_var.get()
                == restored_app._deep_integration_mode_label_for_id("app_server_assisted"),
                "복원 후 deep integration mode가 유지되지 않았습니다.",
            )
            ensure(
                restored_app.deep_app_server_notes_var.get() == "App Server handoff is available.",
                "복원 후 App Server 메모가 유지되지 않았습니다.",
            )
            ensure(
                restored_app.deep_cloud_trigger_notes_var.get() == "Cloud trigger is parked for later.",
                "복원 후 cloud trigger 메모가 유지되지 않았습니다.",
            )
            ensure(
                "Prefer App Server handoff" in restored_app.deep_handoff_note.get("1.0", END),
                "복원 후 handoff note가 유지되지 않았습니다.",
            )
            ensure(
                "App Server assisted" in restored_app.deep_integration_mode_status_var.get(),
                "복원 후 Deep Integration 상태 패널이 다시 계산되지 않았습니다.",
            )
            print_step("deep integration persistence", "mode, readiness note, handoff note가 세션 복원 후에도 유지됩니다.")
        finally:
            try:
                restored_app.control_center.destroy()
            except Exception:
                pass
            restored_root.destroy()

        print("")
        print("[DONE] Release 7 smoke suite passed")
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
