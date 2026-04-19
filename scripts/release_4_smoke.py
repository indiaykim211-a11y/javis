from __future__ import annotations

import sys
import shutil
from pathlib import Path
from tkinter import END, Tk

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


def seed_phase_4_project(app: JavisApp) -> None:
    set_text(app.project_summary, "Release 4 Smoke")
    set_text(app.target_outcome, "판단 엔진이 continue / retry / ask_user를 안정적으로 가른다")
    set_text(
        app.steps_text,
        "\n".join(
            [
                "판단 패킷 생성",
                "판단 결과 표시",
                "위험 신호 시 ask_user로 멈춤",
            ]
        ),
    )
    app.root.update_idletasks()


def prime_runtime(app: JavisApp) -> None:
    app.runtime.next_step_index = 0
    app.runtime.auto_running = False
    app.runtime.clear_operator_pause()
    app.runtime.last_target_title = "Codex"
    app.runtime.last_target_reason = "타깃 창 잠금 유지 상태"
    app.runtime.last_target_score = 98
    app.runtime.target_lock_status = "locked"
    app.runtime.stable_cycles = 4
    app.runtime.last_capture_path = str((app.store.capture_dir / "phase4-smoke.bmp").resolve())


def main() -> None:
    workspace = Path("runtime/release-4-smoke-suite")
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

        ensure(app.control_section_var.get() == "model_voice", "판단 / 모델 섹션으로 이동하지 못했습니다.")
        ensure(app.judgment_engine_combo["values"], "판단 엔진 모드 선택지가 비어 있습니다.")
        seed_phase_4_project(app)
        prime_runtime(app)
        app.refresh_prompt_preview()
        root.update_idletasks()
        print_step("judgment section", "판단 / 모델 섹션과 판단 엔진 설정이 보입니다.")

        set_logs(app, ["[INFO] 현재 단계 준비 완료", "[INFO] 문제 신호 없음"])
        app.run_judgment_now()
        root.update_idletasks()
        ensure(app.runtime.last_judgment.decision == "continue", "정상 흐름에서 continue 판단이 나오지 않았습니다.")
        ensure("continue" in app._current_judgment_response, "continue 판단 응답이 저장되지 않았습니다.")
        ensure(app._surface_state.state_key == "judgment_continue", "continue 팝업 상태가 적용되지 않았습니다.")
        print_step("continue judgment", "정상 상태에서 continue 판단과 popup overlay가 적용됩니다.")

        prime_runtime(app)
        set_logs(app, ["[ERROR] build failed", "[ERROR] 테스트 실패", "[TRACE] exception occurred"])
        app.run_judgment_now()
        root.update_idletasks()
        ensure(app.runtime.last_judgment.decision == "retry", "오류 신호에서 retry 판단이 나오지 않았습니다.")
        ensure(app.runtime.prompt_dirty, "retry 프롬프트가 현재 단계 편집본으로 반영되지 않았습니다.")
        ensure(app._surface_state.state_key == "judgment_retry", "retry 팝업 상태가 적용되지 않았습니다.")
        ensure("보정" in app.popup_badge_var.get() or "retry" in app._current_judgment_response, "retry 요약이 보이지 않습니다.")
        print_step("retry judgment", "오류 신호에서 retry 판단과 보정 프롬프트 반영이 동작합니다.")

        prime_runtime(app)
        set_logs(app, ["[WARN] production deploy pending", "[WARN] billing approval needed"])
        app.run_judgment_now()
        root.update_idletasks()
        ensure(app.runtime.last_judgment.decision == "ask_user", "위험 신호에서 ask_user 판단이 나오지 않았습니다.")
        ensure(app.runtime.operator_paused, "ask_user 판단 후 operator pause가 켜지지 않았습니다.")
        ensure(app._surface_state.state_key == "judgment_pause", "ask_user / pause 팝업 상태가 적용되지 않았습니다.")
        print_step("ask_user judgment", "위험 신호에서 ask_user 판단과 보류 흐름이 적용됩니다.")

        downgraded_high_risk = app.engine.validate_judgment_response(
            {
                "decision": "continue",
                "reason": "위험하지만 계속 가자",
                "confidence": 0.93,
                "risk_level": "high",
                "message_to_user": "그냥 진행",
            },
            session=app.session,
        )
        ensure(
            downgraded_high_risk.decision == "ask_user",
            "high risk continue 응답이 ask_user로 강등되지 않았습니다.",
        )
        downgraded_retry = app.engine.validate_judgment_response(
            {
                "decision": "retry",
                "reason": "다시 시도",
                "confidence": 0.84,
                "risk_level": "medium",
                "message_to_user": "다시 시도",
            },
            session=app.session,
        )
        ensure(downgraded_retry.decision == "pause", "retry without prompt 응답이 pause로 강등되지 않았습니다.")
        print_step("validator downgrade", "high risk continue / 빈 retry prompt가 안전하게 강등됩니다.")

        ensure(len(app.runtime.judgment_history) >= 3, "판단 이력이 3개 이상 쌓이지 않았습니다.")
        ensure("[Judgment Timeline]" in app._current_judgment_timeline, "judgment timeline이 생성되지 않았습니다.")
        app.save_session()
        root.update_idletasks()

        restored_root = Tk()
        restored_app = JavisApp(restored_root, workspace)
        try:
            restored_root.update_idletasks()
            ensure(restored_app.runtime.last_judgment.decision == "ask_user", "재실행 후 마지막 판단이 복원되지 않았습니다.")
            ensure(len(restored_app.runtime.judgment_history) >= 3, "재실행 후 판단 이력이 복원되지 않았습니다.")
            ensure("최근 판단" in restored_app.judgment_result_status_var.get(), "재실행 후 판단 상태 요약이 비어 있습니다.")
            print_step("judgment history", "판단 이력과 마지막 판단 결과가 세션 복원 후에도 유지됩니다.")
        finally:
            try:
                restored_app.control_center.destroy()
            except Exception:
                pass
            restored_root.destroy()

        print("")
        print("[DONE] Release 4 smoke suite passed")
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
