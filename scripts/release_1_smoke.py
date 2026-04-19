from __future__ import annotations

import sys
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


def print_step(title: str, detail: str) -> None:
    print(f"[PASS] {title}: {detail}")


def build_seed_project(app: JavisApp, *, summary: str, target: str, steps: list[str]) -> None:
    set_text(app.project_summary, summary)
    set_text(app.target_outcome, target)
    set_text(app.steps_text, "\n".join(steps))
    app.policy_note_var.set(f"{summary} 정책 메모")
    progress_editor = app.policy_editors["progress_policy"]
    progress_editor.insert("end", "\n- Release 1 스모크 기준으로 애매하면 보류를 우선해 주세요.")
    progress_editor.edit_modified(True)
    app._on_policy_editor_modified("progress_policy")
    app.root.update_idletasks()


def main() -> None:
    workspace = Path("runtime/release-1-smoke-suite")
    workspace.mkdir(parents=True, exist_ok=True)

    root = Tk()
    app = JavisApp(root, workspace)

    try:
        root.update()

        ensure(root.winfo_width() >= 380, "팝업 기본 폭이 너무 작습니다.")
        ensure(not app.popup_compact_frame.winfo_ismapped(), "초기 상태에서 compact 카드가 보이면 안 됩니다.")
        ensure(app.popup_detail_frame.winfo_ismapped(), "초기 상태에서 상세 카드가 보여야 합니다.")
        print_step("popup shell", "기본 팝업 레이아웃이 열렸습니다.")

        app.open_control_center()
        root.update()
        ensure(app.control_center.state() == "normal", "Control Center가 열리지 않았습니다.")
        ensure(app.control_section_var.get() == "project", "Control Center 기본 진입 섹션이 project가 아닙니다.")
        print_step("control center open", "프로젝트 섹션으로 진입했습니다.")

        app.hide_control_center()
        root.update()
        ensure(app.control_center.state() == "withdrawn", "Control Center가 닫히지 않았습니다.")
        print_step("control center close", "팝업으로 자연스럽게 복귀했습니다.")

        build_seed_project(
            app,
            summary="Release 1 Smoke A",
            target="작은 어시스턴트 팝업과 설정창 분리 흐름 검증",
            steps=[
                "프로젝트 입력값 저장",
                "정책 탭 구조 확인",
                "세션 저장 후 복원",
            ],
        )
        app.save_session()
        root.update()

        ensure(app.store.session_path.exists(), "세션 파일이 저장되지 않았습니다.")
        ensure(app.session.project.project_summary == "Release 1 Smoke A", "프로젝트 요약이 저장되지 않았습니다.")
        ensure(app.session.policy.edit_note == "Release 1 Smoke A 정책 메모", "정책 메모가 저장되지 않았습니다.")
        ensure(len(app.recent_projects) >= 1, "최근 프로젝트가 쌓이지 않았습니다.")
        print_step("session save", "프로젝트와 정책 메모가 저장되었습니다.")

        app.toggle_popup_compact()
        root.update()
        ensure(app.popup_compact_frame.winfo_ismapped(), "compact 카드가 보이지 않습니다.")
        ensure(not app.popup_detail_frame.winfo_ismapped(), "compact 상태에서 상세 카드가 숨겨지지 않았습니다.")
        compact_layout = [(btn.grid_info().get("row"), btn.grid_info().get("column")) for btn in app.popup_action_buttons]
        ensure(compact_layout == [(0, 0), (0, 1), (1, 0), (1, 1)], "좁은 폭 버튼 배치가 2x2가 아닙니다.")
        print_step("compact mode", "compact 카드와 2x2 버튼 레이아웃이 확인되었습니다.")

        app.toggle_popup_compact()
        root.update()
        ensure(app.popup_detail_frame.winfo_ismapped(), "상세 모드로 복귀하지 못했습니다.")
        print_step("expanded mode", "상세 모드로 정상 복귀했습니다.")

        button_labels = [button.cget("text").strip() for button in app.popup_action_buttons]
        ensure(any(label for label in button_labels), "팝업 액션 버튼 라벨이 비어 있습니다.")
        app.pause_automation()
        ensure(app.runtime.operator_paused, "보류 상태로 전환되지 않았습니다.")
        app.resume_after_pause()
        ensure(not app.runtime.operator_paused, "보류 상태가 해제되지 않았습니다.")
        print_step("popup actions", f"버튼 라벨 {button_labels} / 보류-재개 흐름 확인")

        app.open_control_center()
        root.update()
        build_seed_project(
            app,
            summary="Release 1 Smoke B",
            target="최근 프로젝트 복원 흐름 검증",
            steps=[
                "서로 다른 프로젝트 2개 저장",
                "이전 프로젝트 선택",
                "값 복원 확인",
            ],
        )
        app.save_session()
        root.update()
        ensure(len(app.recent_projects) >= 2, "최근 프로젝트가 2개 이상 쌓이지 않았습니다.")

        app.recent_projects_combo.current(1)
        app.load_recent_project_selection()
        root.update()
        ensure(app.session.project.project_summary == "Release 1 Smoke A", "최근 프로젝트 복원이 실패했습니다.")
        ensure("현재 단계" in app.project_home_progress_var.get() or "진행" in app.project_home_progress_var.get(), "프로젝트 홈 진행 정보가 비어 있습니다.")
        app.save_session()
        root.update()
        print_step("recent project restore", "이전 프로젝트를 다시 불러왔습니다.")

        restored_root = Tk()
        restored_app = JavisApp(restored_root, workspace)
        try:
            restored_root.update()
            ensure(
                restored_app.session.project.project_summary == "Release 1 Smoke A",
                "재실행 후 저장된 세션이 복원되지 않았습니다.",
            )
            ensure(
                restored_app.session.policy.edit_note == "Release 1 Smoke A 정책 메모",
                "재실행 후 정책 메모가 복원되지 않았습니다.",
            )
            print_step("relaunch restore", "재실행 후 세션과 정책 메모가 복원되었습니다.")
        finally:
            restored_app.control_center.destroy()
            restored_root.destroy()

        print("")
        print("[DONE] Release 1 smoke suite passed")
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
