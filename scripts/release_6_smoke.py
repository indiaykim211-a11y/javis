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


def seed_phase_6_project(app: JavisApp) -> None:
    set_text(app.project_summary, "Release 6 Smoke")
    set_text(app.target_outcome, "voice command와 spoken briefing으로 Codex 운영 흐름을 더 쉽게 제어한다")
    set_text(
        app.steps_text,
        "\n".join(
            [
                "현재 상태를 voice로 요약한다",
                "필요하면 보류 이유를 읽어준다",
                "고위험 continue는 confirmation gate를 건다",
            ]
        ),
    )
    app.voice_language_var.set("ko-KR")
    app.voice_microphone_var.set("Default Microphone")
    app.voice_speaker_var.set("Default Speaker")
    app.voice_auto_brief_var.set(True)
    app.voice_confirmation_var.set(True)
    app.voice_spoken_feedback_var.set(True)
    app.voice_ambient_ready_var.set(False)
    app.root.update_idletasks()


def prime_runtime(app: JavisApp, workspace: Path) -> None:
    capture_dir = workspace / "captures"
    capture_dir.mkdir(parents=True, exist_ok=True)
    capture_path = capture_dir / "phase6-smoke.bmp"
    capture_path.write_bytes(b"BM")

    app.runtime = RuntimeState()
    app.runtime.next_step_index = 0
    app.runtime.auto_running = False
    app.runtime.clear_operator_pause()
    app.runtime.last_target_title = "Codex"
    app.runtime.last_target_reason = "voice smoke target is ready"
    app.runtime.last_target_score = 98
    app.runtime.target_lock_status = "locked"
    app.runtime.stable_cycles = 5
    app.runtime.last_capture_path = str(capture_path.resolve())


def main() -> None:
    workspace = Path("runtime/release-6-smoke-suite")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    root = Tk()
    app = JavisApp(root, workspace)

    try:
        root.update_idletasks()
        app.open_control_center()
        app._select_control_center_section("model_voice")
        root.update_idletasks()

        ensure(app.control_section_var.get() == "model_voice", "판단 / 모델 / 음성 섹션으로 이동하지 못했습니다.")
        ensure(app.voice_language_var.get().strip(), "voice language 기본값이 비어 있습니다.")
        print_step("voice section", "Phase 6 Control Center 섹션과 voice 설정 필드가 보입니다.")

        seed_phase_6_project(app)
        prime_runtime(app, workspace)
        app.refresh_prompt_preview()
        root.update_idletasks()

        set_text(app.voice_transcript_input, "지금 상태 요약해줘")
        app.run_voice_command_now()
        root.update_idletasks()
        ensure(app.runtime.last_voice_result.normalized_intent_id == "status_summary", "status_summary intent로 해석되지 않았습니다.")
        ensure(app.runtime.last_voice_result.action_status == "executed", "상태 요약이 실행 상태로 끝나지 않았습니다.")
        ensure(app._current_voice_briefing.strip(), "spoken briefing 초안이 생성되지 않았습니다.")
        print_step("voice summary", "현재 상태 요약 intent와 spoken briefing 초안이 생성됩니다.")

        set_text(app.voice_transcript_input, "멈춰")
        app.run_voice_command_now()
        root.update_idletasks()
        ensure(app.runtime.operator_paused, "voice pause 후 operator pause가 켜지지 않았습니다.")
        ensure(app.runtime.last_voice_result.normalized_intent_id == "pause_run", "pause_run intent가 기록되지 않았습니다.")
        print_step("voice pause", "voice pause 명령이 보류 상태와 briefing으로 연결됩니다.")

        set_text(app.voice_transcript_input, "왜 멈췄어")
        app.run_voice_command_now()
        root.update_idletasks()
        ensure(app.runtime.last_voice_result.normalized_intent_id == "why_paused", "why_paused intent가 기록되지 않았습니다.")
        ensure(
            "보류" in app._current_voice_briefing or "멈" in app._current_voice_briefing,
            "보류 이유 briefing이 생성되지 않았습니다.",
        )
        print_step("pause briefing", "보류 상태에서 why_paused 브리핑을 읽어줍니다.")

        app.session = app._collect_session()
        confirmation_result = app.engine.run_voice_command(app.session, app.runtime, "다음 단계 진행해")
        app._refresh_voice_panel(app.session)
        root.update_idletasks()
        ensure(confirmation_result.action_status == "confirmation_required", "고위험 continue가 confirmation gate로 승격되지 않았습니다.")
        ensure(app.runtime.voice_pending_action_id == "continue", "continue confirmation이 pending 상태로 남지 않았습니다.")
        print_step("confirmation gate", "보류 중 continue 요청은 voice confirmation gate로 전환됩니다.")

        app.cancel_pending_voice_action()
        root.update_idletasks()
        ensure(not app.runtime.voice_pending_action_id, "voice confirmation 취소 후 pending action이 남아 있습니다.")
        ensure(app.runtime.last_voice_result.normalized_intent_id == "confirm_no", "취소 결과가 confirm_no로 기록되지 않았습니다.")
        print_step("confirmation cancel", "대기 중 confirmation을 취소하면 pending 상태가 정리됩니다.")

        app.runtime.set_voice_pending_confirmation("open_settings", "설정 창을 다시 열기 전에 확인이 필요합니다.")
        app._refresh_voice_panel(app.session)
        root.update_idletasks()
        app.confirm_pending_voice_action()
        root.update_idletasks()
        ensure(not app.runtime.voice_pending_action_id, "확인 후 pending action이 남아 있습니다.")
        ensure(app.runtime.last_voice_result.normalized_intent_id == "confirm_yes", "확인 결과가 confirm_yes로 기록되지 않았습니다.")
        ensure(app.control_section_var.get() == "model_voice", "voice confirmation으로 설정 창을 다시 열지 못했습니다.")
        print_step("confirmation confirm", "확인된 voice action은 안전한 UI 액션으로 이어집니다.")

        app.perform_surface_action("voice_brief")
        root.update_idletasks()
        ensure(app._current_voice_briefing.strip(), "surface voice_brief 액션이 briefing을 만들지 못했습니다.")
        print_step("surface action", "팝업 action router에서도 voice briefing을 실행할 수 있습니다.")

        app.toggle_voice_capture()
        root.update_idletasks()
        ensure(app.runtime.voice_capture_state == "recording", "push-to-talk 토글이 recording으로 바뀌지 않았습니다.")
        app.toggle_voice_capture()
        root.update_idletasks()
        ensure(app.runtime.voice_capture_state == "idle", "push-to-talk 토글이 idle로 돌아오지 않았습니다.")
        print_step("push-to-talk shell", "capture shell 토글이 recording/idle 상태를 전환합니다.")

        ensure(len(app.runtime.voice_history) >= 5, "voice history가 충분히 쌓이지 않았습니다.")

        app.save_session()
        root.update_idletasks()

        restored_root = Tk()
        restored_app = JavisApp(restored_root, workspace)
        try:
            restored_root.update_idletasks()
            restored_app.open_control_center()
            restored_app._select_control_center_section("model_voice")
            restored_root.update_idletasks()
            ensure(restored_app.runtime.last_voice_result.normalized_intent_id == "confirm_yes", "재시작 후 마지막 voice result가 복원되지 않았습니다.")
            ensure(len(restored_app.runtime.voice_history) >= 5, "재시작 후 voice history가 복원되지 않았습니다.")
            ensure(restored_app.runtime.voice_last_briefing.strip(), "재시작 후 마지막 voice briefing이 비어 있습니다.")
            ensure(restored_app.voice_language_var.get() == "ko-KR", "재시작 후 voice language 설정이 복원되지 않았습니다.")
            print_step("voice persistence", "voice 설정, 마지막 결과, history가 세션 복원 후에도 유지됩니다.")
        finally:
            try:
                restored_app.control_center.destroy()
            except Exception:
                pass
            restored_root.destroy()

        print("")
        print("[DONE] Release 6 smoke suite passed")
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
