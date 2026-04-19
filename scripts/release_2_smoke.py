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


def seed_phase_2_project(app: JavisApp, *, summary: str, target: str, steps: list[str]) -> None:
    set_text(app.project_summary, summary)
    set_text(app.target_outcome, target)
    set_text(app.steps_text, "\n".join(steps))
    set_text(app.codex_strategy_note, "애매하면 ask_user로 멈추고, nightly brief는 짧게 보고")
    app.root.update_idletasks()


def main() -> None:
    workspace = Path("runtime/release-2-smoke-suite")
    workspace.mkdir(parents=True, exist_ok=True)

    root = Tk()
    app = JavisApp(root, workspace)

    try:
        root.update_idletasks()
        app.open_control_center()
        root.update_idletasks()
        app._select_control_center_section("codex_strategy")
        root.update_idletasks()

        ensure(app.control_section_var.get() == "codex_strategy", "Codex 전략 섹션으로 이동하지 못했습니다.")
        ensure(app.codex_strategy_combo["values"], "전략 프리셋이 비어 있습니다.")
        print_step("strategy section", "Codex 전략 섹션과 프리셋 목록이 보입니다.")

        seed_phase_2_project(
            app,
            summary="Release 2 Smoke A",
            target="Codex-first 전략 센터와 운영 프로필 검증",
            steps=[
                "Codex 전략 프리셋 선택",
                "prompt 초안 생성",
                "운영 프로필 저장 및 복원",
            ],
        )
        nightly_label = app._codex_strategy_label_for_id("nightly_brief")
        app.codex_strategy_var.set(nightly_label)
        app.refresh_codex_strategy_prompt()
        root.update_idletasks()

        prompt_text = app.codex_strategy_prompt_preview.get("1.0", END).strip()
        runbook_text = app.codex_strategy_runbook_preview.get("1.0", END).strip()
        matrix_text = app.native_fallback_preview.get("1.0", END).strip()

        ensure("Release 2 Smoke A" in prompt_text, "prompt 초안에 프로젝트 요약이 반영되지 않았습니다.")
        ensure("nightly" in prompt_text.lower() or "Nightly Project Brief" in prompt_text, "nightly 프리셋 prompt가 아닙니다.")
        ensure("추가 지시" in prompt_text, "추가 지시가 prompt 초안에 반영되지 않았습니다.")
        ensure("standalone / project automation" in runbook_text, "런북에 project automation 안내가 없습니다.")
        ensure("fallback" in matrix_text.lower(), "매트릭스에 fallback 원칙이 없습니다.")
        print_step("prompt and guidance", "prompt / 런북 / 매트릭스가 현재 전략 기준으로 생성되었습니다.")

        app.save_session()
        root.update_idletasks()
        ensure(app.session.codex_strategy.selected_preset_id == "nightly_brief", "선택된 전략이 저장되지 않았습니다.")
        ensure("Nightly Project Brief" in app.project_home_strategy_var.get(), "현재 프로젝트 카드에 운영 프로필이 보이지 않습니다.")
        ensure(len(app.recent_projects) >= 1, "최근 프로젝트가 저장되지 않았습니다.")
        print_step("save profile", "운영 프로필이 세션과 현재 프로젝트 카드에 저장되었습니다.")

        seed_phase_2_project(
            app,
            summary="Release 2 Smoke B",
            target="다른 운영 전략 저장",
            steps=[
                "release smoke 프리셋 선택",
                "저장 후 최근 프로젝트 비교",
            ],
        )
        release_smoke_label = app._codex_strategy_label_for_id("release_smoke")
        app.codex_strategy_var.set(release_smoke_label)
        app.refresh_codex_strategy_prompt()
        app.save_session()
        root.update_idletasks()
        ensure(len(app.recent_projects) >= 2, "최근 프로젝트가 2개 이상 쌓이지 않았습니다.")

        app.recent_projects_combo.current(1)
        app.load_recent_project_selection()
        root.update_idletasks()
        ensure(app.session.project.project_summary == "Release 2 Smoke A", "최근 프로젝트 복원이 실패했습니다.")
        ensure(app.session.codex_strategy.selected_preset_id == "nightly_brief", "운영 프로필 복원이 실패했습니다.")
        ensure("Nightly Project Brief" in app.project_home_strategy_var.get(), "복원 후 운영 프로필 카드가 갱신되지 않았습니다.")
        print_step("recent restore", "최근 프로젝트와 운영 프로필이 함께 복원되었습니다.")

        restored_root = Tk()
        restored_app = JavisApp(restored_root, workspace)
        try:
            restored_root.update_idletasks()
            ensure(
                restored_app.session.project.project_summary == "Release 2 Smoke A",
                "재실행 후 Phase 2 세션이 복원되지 않았습니다.",
            )
            ensure(
                restored_app.session.codex_strategy.selected_preset_id == "nightly_brief",
                "재실행 후 Codex 전략이 복원되지 않았습니다.",
            )
            ensure(
                "Nightly Project Brief" in restored_app.project_home_strategy_var.get(),
                "재실행 후 운영 프로필 카드가 비어 있습니다.",
            )
            print_step("relaunch restore", "재실행 후 전략 선택과 운영 프로필이 복원되었습니다.")
        finally:
            restored_app.control_center.destroy()
            restored_root.destroy()

        print("")
        print("[DONE] Release 2 smoke suite passed")
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
