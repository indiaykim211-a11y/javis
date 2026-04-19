from __future__ import annotations

import shutil
import sys
from pathlib import Path
from tkinter import END, Tk

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models import JudgmentResult, RuntimeState, VisualEvidenceResult
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


def set_logs(app: JavisApp, lines: list[str]) -> None:
    app.log_text.configure(state="normal")
    app.log_text.delete("1.0", END)
    app.log_text.insert("1.0", "\n".join(lines) + ("\n" if lines else ""))
    app.log_text.configure(state="disabled")


def print_step(title: str, detail: str) -> None:
    print(f"[PASS] {title}: {detail}")


def seed_phase_5_project(app: JavisApp) -> None:
    set_text(app.project_summary, "Release 5 Smoke")
    set_text(app.target_outcome, "visual evidence로 contradiction을 감지하고 judgment에 다시 연결한다")
    set_text(
        app.steps_text,
        "\n".join(
            [
                "visual packet 만든다",
                "contradiction 판단한다",
                "필요하면 retry 또는 ask_user로 연결한다",
            ]
        ),
    )
    app.visual_target_mode_var.set(app._visual_target_label_for_id("browser_result"))
    app.visual_capture_scope_var.set(app._visual_scope_label_for_id("targeted_only"))
    app.visual_retention_var.set(app._visual_retention_label_for_id("short"))
    app.visual_sensitive_risk_var.set("medium")
    app.root.update_idletasks()


def prime_runtime(app: JavisApp, workspace: Path) -> None:
    capture_dir = workspace / "captures"
    capture_dir.mkdir(parents=True, exist_ok=True)
    capture_path = capture_dir / "phase5-smoke.bmp"
    capture_path.write_bytes(b"BM")

    history = list(app.runtime.visual_history)
    judgment_history = list(app.runtime.judgment_history)

    app.runtime = RuntimeState()
    app.runtime.visual_history = history
    app.runtime.judgment_history = judgment_history
    app.runtime.next_step_index = 0
    app.runtime.auto_running = False
    app.runtime.clear_operator_pause()
    app.runtime.last_target_title = "Codex"
    app.runtime.last_target_reason = "visual smoke target is ready"
    app.runtime.last_target_score = 97
    app.runtime.target_lock_status = "locked"
    app.runtime.stable_cycles = 4
    app.runtime.last_capture_path = str(capture_path.resolve())
    app.runtime.last_judgment = JudgmentResult()
    app.runtime.last_visual_result = VisualEvidenceResult()


def main() -> None:
    workspace = Path("runtime/release-5-smoke-suite")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    root = Tk()
    app = JavisApp(root, workspace)

    try:
        root.update_idletasks()
        app.open_control_center()
        app._select_control_center_section("visual")
        root.update_idletasks()

        ensure(app.control_section_var.get() == "visual", "시각 감독 섹션으로 이동하지 못했습니다.")
        ensure(app.visual_target_combo["values"], "시각 감독 target mode 선택지가 비어 있습니다.")

        seed_phase_5_project(app)
        prime_runtime(app, workspace)
        app.refresh_prompt_preview()
        root.update_idletasks()

        set_text(app.visual_expected_page, "settings dashboard")
        set_text(app.visual_focus, "cta visibility\nblank screen\nroute mismatch")
        set_text(app.visual_expected_signals, "save button\nsuccess badge")
        set_text(app.visual_disallowed_signals, "wrong route\nerror banner")
        set_text(
            app.visual_observed_notes,
            "settings dashboard is visible. save button and success badge are present.",
        )
        set_logs(app, ["[INFO] settings dashboard rendered", "[INFO] save button visible"])
        app.refresh_visual_evidence()
        root.update_idletasks()
        ensure('"effective_target_type": "browser_result"' in app._current_visual_packet, "visual packet target planner가 browser_result로 잡히지 않았습니다.")
        ensure("phase5-smoke.bmp" in app._current_visual_packet, "최근 capture가 visual packet에 연결되지 않았습니다.")
        print_step("visual packet", "target planner와 capture evidence가 visual packet에 들어갑니다.")

        app.run_visual_rejudge_now()
        root.update_idletasks()
        ensure(app.runtime.last_visual_result.decision_hint == "continue", "정상 화면에서 continue hint가 나오지 않았습니다.")
        ensure(app.runtime.last_judgment.decision == "continue", "정상 화면에서 continue judgment가 나오지 않았습니다.")
        ensure(not app.runtime.operator_paused, "continue judgment인데 operator pause가 남아 있습니다.")
        print_step("visual continue", "정상 관찰에서는 contradiction 없이 continue로 이어집니다.")

        prime_runtime(app, workspace)
        set_text(app.visual_expected_page, "settings dashboard")
        set_text(app.visual_expected_signals, "save button\nprimary cta")
        set_text(app.visual_disallowed_signals, "missing button")
        set_text(
            app.visual_observed_notes,
            "settings dashboard loaded but save button is missing and primary cta is missing.",
        )
        set_logs(app, ["[INFO] dashboard rendered", "[INFO] missing button detected"])
        app.run_visual_rejudge_now()
        root.update_idletasks()
        ensure(app.runtime.last_visual_result.contradiction_detected, "missing button 관찰인데 contradiction이 감지되지 않았습니다.")
        ensure(app.runtime.last_visual_result.decision_hint == "retry", "medium contradiction에서 retry hint가 나오지 않았습니다.")
        ensure(app.runtime.last_judgment.decision == "retry", "medium contradiction에서 retry judgment가 나오지 않았습니다.")
        ensure(app.runtime.prompt_dirty, "retry judgment인데 보정 프롬프트가 draft에 반영되지 않았습니다.")
        print_step("visual retry", "중간 수준 모순은 retry와 보정 프롬프트로 연결됩니다.")

        prime_runtime(app, workspace)
        set_text(app.visual_expected_page, "checkout success page")
        set_text(app.visual_expected_signals, "receipt card")
        set_text(app.visual_disallowed_signals, "wrong route\nerror")
        set_text(
            app.visual_observed_notes,
            "wrong route is visible and an error banner blocks the page.",
        )
        set_logs(app, ["[WARN] wrong route opened", "[ERROR] error banner visible"])
        app.run_visual_rejudge_now()
        root.update_idletasks()
        ensure(app.runtime.last_visual_result.contradiction_level == "high", "high contradiction이 감지되지 않았습니다.")
        ensure(app.runtime.last_judgment.decision == "ask_user", "high contradiction에서 ask_user judgment가 나오지 않았습니다.")
        ensure(app.runtime.operator_paused, "ask_user judgment인데 operator pause가 켜지지 않았습니다.")
        print_step("visual ask_user", "강한 모순은 ask_user와 pause로 승격됩니다.")

        ensure(len(app.runtime.visual_history) >= 3, "visual history가 3개 이상 쌓이지 않았습니다.")
        ensure(len(app.runtime.judgment_history) >= 3, "judgment history가 3개 이상 쌓이지 않았습니다.")
        ensure("[Visual Timeline]" in app._current_visual_timeline, "visual timeline이 생성되지 않았습니다.")

        app.save_session()
        root.update_idletasks()

        restored_root = Tk()
        restored_app = JavisApp(restored_root, workspace)
        try:
            restored_root.update_idletasks()
            restored_app.open_control_center()
            restored_app._select_control_center_section("visual")
            restored_root.update_idletasks()
            ensure(restored_app.runtime.last_visual_result.contradiction_level == "high", "재시작 후 마지막 visual contradiction이 복원되지 않았습니다.")
            ensure(restored_app.runtime.last_judgment.decision == "ask_user", "재시작 후 마지막 judgment가 복원되지 않았습니다.")
            ensure(len(restored_app.runtime.visual_history) >= 3, "재시작 후 visual history가 복원되지 않았습니다.")
            ensure("contradiction" in restored_app.visual_summary_status_var.get(), "재시작 후 visual summary 상태가 비어 있습니다.")
            print_step("visual persistence", "visual result와 history가 세션 복원 후에도 유지됩니다.")
        finally:
            try:
                restored_app.control_center.destroy()
            except Exception:
                pass
            restored_root.destroy()

        print("")
        print("[DONE] Release 5 smoke suite passed")
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
