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


def print_step(title: str, detail: str) -> None:
    print(f"[PASS] {title}: {detail}")


def seed_phase_3_project(app: JavisApp, *, summary: str, target: str, steps: list[str], note: str) -> None:
    set_text(app.project_summary, summary)
    set_text(app.target_outcome, target)
    set_text(app.steps_text, "\n".join(steps))
    set_text(app.codex_strategy_note, note)
    app.root.update_idletasks()


def main() -> None:
    workspace = Path("runtime/release-3-smoke-suite")
    if workspace.exists():
        shutil.rmtree(workspace)
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
        ensure(app.codex_mode_combo["values"], "automation mode 선택지가 비어 있습니다.")
        print_step("strategy section", "Phase 3 전략 센터와 mode 선택기가 보입니다.")

        seed_phase_3_project(
            app,
            summary="Release 3 Smoke A",
            target="같은 스레드 no automation 흐름 검증",
            steps=[
                "mode 추천 확인",
                "같은 스레드 prompt 생성",
                "runboard / triage bridge 확인",
            ],
            note="마스터플랜이 있으면 no automation을 먼저 보고, 애매하면 ask_user로 멈춰 주세요.",
        )
        app.codex_strategy_var.set(app._codex_strategy_label_for_id("masterplan_followup"))
        app.codex_mode_var.set(app._codex_mode_label_for_id("recommended"))
        app.refresh_codex_strategy_prompt()
        root.update_idletasks()

        prompt_text = app.codex_strategy_prompt_preview.get("1.0", END).strip()
        runbook_text = app.codex_strategy_runbook_preview.get("1.0", END).strip()
        runboard_text = app.automation_runboard_preview.get("1.0", END).strip()
        triage_text = app.triage_bridge_preview.get("1.0", END).strip()
        safety_text = app.native_fallback_preview.get("1.0", END).strip()

        ensure("no automation" in app.codex_mode_status_var.get().lower(), "추천 mode가 no automation으로 보이지 않습니다.")
        ensure("이 현재 스레드에서 이 프로젝트를 순차적으로 진행해 주세요." in prompt_text, "no automation prompt가 아닙니다.")
        ensure("automation을 만들지 않고 현재 운영 스레드" in runbook_text, "no automation launch flow가 아닙니다.")
        ensure("[Automation Runboard]" in runboard_text, "runboard가 생성되지 않았습니다.")
        ensure("[Triage / Re-entry Bridge]" in triage_text, "triage bridge가 생성되지 않았습니다.")
        ensure("[Automation Safety Guard]" in safety_text, "safety guard가 생성되지 않았습니다.")
        app.save_session()
        root.update_idletasks()
        ensure(app.session.codex_strategy.selected_mode_id == "recommended", "recommended mode가 저장되지 않았습니다.")
        print_step("no automation mode", "추천 mode, launch prompt, runboard, triage bridge, safety guard가 생성되었습니다.")

        app.codex_mode_var.set(app._codex_mode_label_for_id("thread_automation"))
        app.refresh_codex_strategy_prompt()
        root.update_idletasks()
        prompt_text = app.codex_strategy_prompt_preview.get("1.0", END).strip()
        runbook_text = app.codex_strategy_runbook_preview.get("1.0", END).strip()
        ensure("thread automation용 작업 설명" in prompt_text, "thread automation prompt가 아닙니다.")
        ensure("thread automation 생성 화면" in runbook_text, "thread launch flow가 아닙니다.")
        ensure("thread automation 결과" in app.codex_mode_result_var.get() or "thread automation 결과" in triage_text, "thread 결과 안내가 없습니다.")
        print_step("thread override", "thread automation override 시 prompt와 launch flow가 함께 바뀝니다.")

        app.codex_mode_var.set(app._codex_mode_label_for_id("recommended"))
        app.refresh_codex_strategy_prompt()
        app.save_session()
        root.update_idletasks()

        seed_phase_3_project(
            app,
            summary="Release 3 Smoke B",
            target="독립 project automation 흐름 검증",
            steps=[
                "nightly brief 전략 선택",
                "project automation prompt 생성",
                "저장 후 복원",
            ],
            note="nightly brief는 짧게 보고하고, 결과는 Triage에서 다시 확인하게 해 주세요.",
        )
        app.codex_strategy_var.set(app._codex_strategy_label_for_id("nightly_brief"))
        app.codex_mode_var.set(app._codex_mode_label_for_id("project_automation"))
        app.refresh_codex_strategy_prompt()
        root.update_idletasks()

        prompt_text = app.codex_strategy_prompt_preview.get("1.0", END).strip()
        runbook_text = app.codex_strategy_runbook_preview.get("1.0", END).strip()
        triage_text = app.triage_bridge_preview.get("1.0", END).strip()
        ensure("독립 project automation용 작업 설명" in prompt_text, "project automation prompt가 아닙니다.")
        ensure("standalone / project automation" in runbook_text, "project automation launch flow가 아닙니다.")
        ensure("Triage" in triage_text, "project automation triage bridge가 아닙니다.")

        app.save_session()
        root.update_idletasks()
        ensure(app.session.codex_strategy.selected_mode_id == "project_automation", "project automation mode가 저장되지 않았습니다.")
        ensure("실제 launch" in app.project_home_strategy_var.get(), "현재 프로젝트 카드에 launch mode가 보이지 않습니다.")
        print_step("project automation mode", "project automation prompt와 저장 흐름이 확인되었습니다.")

        ensure(len(app.recent_projects) >= 2, "최근 프로젝트가 2개 이상 쌓이지 않았습니다.")
        app.recent_projects_combo.current(1)
        app.load_recent_project_selection()
        root.update_idletasks()
        ensure(app.session.project.project_summary == "Release 3 Smoke A", "최근 프로젝트 복원이 실패했습니다.")
        ensure(app.session.codex_strategy.selected_mode_id == "recommended", "recent project의 mode가 복원되지 않았습니다.")
        ensure("선택 mode" in app.project_home_strategy_var.get(), "프로젝트 홈 카드에 mode 정보가 없습니다.")
        print_step("recent restore", "최근 프로젝트와 mode 선택이 함께 복원되었습니다.")

        restored_root = Tk()
        restored_app = JavisApp(restored_root, workspace)
        try:
            restored_root.update_idletasks()
            ensure(restored_app.session.project.project_summary == "Release 3 Smoke A", "재실행 후 Phase 3 세션이 복원되지 않았습니다.")
            ensure(restored_app.session.codex_strategy.selected_mode_id == "recommended", "재실행 후 mode 선택이 복원되지 않았습니다.")
            ensure("실제 launch" in restored_app.project_home_strategy_var.get(), "재실행 후 프로젝트 카드에 launch mode가 비어 있습니다.")
            ensure(
                "no automation" in restored_app.codex_mode_status_var.get().lower(),
                "재실행 후 추천 mode가 no automation으로 보이지 않습니다.",
            )
            print_step("relaunch restore", "재실행 후 mode 선택과 launch 카드가 복원되었습니다.")
        finally:
            restored_app.control_center.destroy()
            restored_root.destroy()

        print("")
        print("[DONE] Release 3 smoke suite passed")
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
