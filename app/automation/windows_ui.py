from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.automation.powershell_runner import run_powershell
from app.models import WindowTarget


USER32_TYPES = r"""
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public struct RECT {
    public int Left;
    public int Top;
    public int Right;
    public int Bottom;
}

public struct POINT {
    public int X;
    public int Y;
}

public static class NativeMethods {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int x, int y);

    [DllImport("user32.dll")]
    public static extern bool GetCursorPos(out POINT point);

    [DllImport("user32.dll")]
    public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extraInfo);
}
"@
"""


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


@dataclass
class WindowInfo:
    title: str
    process_name: str
    process_id: int
    handle: int


@dataclass
class WindowRect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(self.right - self.left, 0)

    @property
    def height(self) -> int:
        return max(self.bottom - self.top, 0)

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x <= self.right and self.top <= y <= self.bottom

    def to_relative(self, x: int, y: int) -> tuple[int, int]:
        return x - self.left, y - self.top


@dataclass
class WindowCandidate:
    window: WindowInfo
    score: int
    reasons: list[str] = field(default_factory=list)

    @property
    def reason_text(self) -> str:
        return ", ".join(self.reasons) if self.reasons else "근거 없음"

    def format_line(self, selected_handle: int | None = None) -> str:
        marker = "*" if selected_handle is not None and self.window.handle == selected_handle else " "
        return (
            f"{marker} {self.score:>3} | "
            f"{self.window.process_name:<14} | "
            f"PID {self.window.process_id:<6} | "
            f"HWND {self.window.handle:<8} | "
            f"{self.window.title} | "
            f"{self.reason_text}"
        )


@dataclass
class WindowResolution:
    selected: WindowInfo | None
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    candidates: list[WindowCandidate] = field(default_factory=list)
    lock_reused: bool = False
    lock_lost: bool = False

    @property
    def reason_text(self) -> str:
        return ", ".join(self.reasons) if self.reasons else ""

    @property
    def lock_status(self) -> str:
        if self.selected is None:
            if self.lock_lost:
                return "잠금 창 상실"
            return "타겟 없음"
        if self.lock_reused:
            return "이전 성공 창 유지"
        if self.lock_lost:
            return "잠금 창 상실 후 재탐색"
        return "새 후보 선택"

    def summary(self) -> str:
        if self.selected is None:
            if self.lock_lost:
                return "이전 잠금 창이 사라져 재탐색했지만 Codex 창을 찾지 못했습니다."
            return "조건에 맞는 Codex 창을 찾지 못했습니다."

        prefix = {
            "이전 성공 창 유지": "이전 성공 창을 그대로 사용합니다.",
            "잠금 창 상실 후 재탐색": "이전 잠금 창이 사라져 가장 점수가 높은 후보로 전환했습니다.",
            "새 후보 선택": "현재 가장 점수가 높은 Codex 창을 선택했습니다.",
        }.get(self.lock_status, "Codex 창을 선택했습니다.")
        reasons = f" 근거: {self.reason_text}." if self.reason_text else ""
        return f"{prefix} 점수 {self.score}.{reasons}"


class WindowsDesktopBridge:
    def list_windows(self) -> list[WindowInfo]:
        script = r"""
Get-Process |
Where-Object { $_.MainWindowTitle -ne '' -and $_.MainWindowHandle -ne 0 } |
ForEach-Object {
    [PSCustomObject]@{
        title = $_.MainWindowTitle
        processName = $_.ProcessName
        processId = $_.Id
        handle = [int64]$_.MainWindowHandle
    }
} |
ConvertTo-Json -Depth 3
"""
        raw = run_powershell(script)
        if not raw:
            return []
        payload = json.loads(raw)
        if isinstance(payload, dict):
            payload = [payload]
        return [
            WindowInfo(
                title=item["title"],
                process_name=item["processName"],
                process_id=int(item["processId"]),
                handle=int(item["handle"]),
            )
            for item in payload
        ]

    def find_windows(self, title_contains: str, process_name: str) -> list[WindowInfo]:
        title_needle = title_contains.lower().strip()
        process_needle = process_name.lower().strip()
        matches = []
        for window in self.list_windows():
            if title_needle and title_needle not in window.title.lower():
                continue
            if process_needle and process_needle not in window.process_name.lower():
                continue
            matches.append(window)
        return matches

    def resolve_target(self, target: WindowTarget) -> WindowResolution:
        windows = self.list_windows()
        lock_lost = bool(
            target.last_handle is not None
            and all(window.handle != target.last_handle for window in windows)
        )

        candidates = []
        for window in windows:
            candidate = self._score_window(window, target)
            if candidate is not None:
                candidates.append(candidate)

        candidates.sort(
            key=lambda item: (-item.score, item.window.process_id, item.window.handle)
        )
        if not candidates:
            return WindowResolution(
                selected=None,
                candidates=[],
                lock_reused=False,
                lock_lost=lock_lost,
            )

        selected_candidate = candidates[0]
        return WindowResolution(
            selected=selected_candidate.window,
            score=selected_candidate.score,
            reasons=selected_candidate.reasons,
            candidates=candidates,
            lock_reused=(
                target.last_handle is not None
                and selected_candidate.window.handle == target.last_handle
            ),
            lock_lost=lock_lost,
        )

    def _score_window(self, window: WindowInfo, target: WindowTarget) -> WindowCandidate | None:
        title_needle = target.title_contains.lower().strip()
        process_needle = target.process_name.lower().strip()
        title_lower = window.title.lower()
        process_lower = window.process_name.lower()

        score = 0
        reasons: list[str] = []

        if process_needle:
            if process_lower == process_needle:
                score += 130
                reasons.append("프로세스 정확 일치")
            elif process_needle in process_lower:
                score += 90
                reasons.append("프로세스 부분 일치")

        if title_needle:
            if title_lower == title_needle:
                score += 100
                reasons.append("제목 정확 일치")
            elif title_needle in title_lower:
                score += 70
                reasons.append("제목 포함 일치")

        if target.last_handle is not None and window.handle == target.last_handle:
            score += 260
            reasons.append("이전 성공 핸들 일치")

        if target.last_process_id is not None and window.process_id == target.last_process_id:
            score += 140
            reasons.append("이전 성공 프로세스 일치")

        last_title = target.last_title.lower().strip()
        if last_title:
            if title_lower == last_title:
                score += 80
                reasons.append("이전 성공 제목 일치")
            elif last_title in title_lower:
                score += 40
                reasons.append("이전 성공 제목 유사")

        last_process_name = target.last_process_name.lower().strip()
        if last_process_name and process_lower == last_process_name:
            score += 50
            reasons.append("이전 성공 프로세스명 일치")

        if not reasons:
            return None
        return WindowCandidate(window=window, score=score, reasons=reasons)

    def get_window_rect(self, handle: int) -> WindowRect:
        script = f"""
{USER32_TYPES}
$handle = [IntPtr]::new({handle})
$rect = New-Object RECT
$ok = [NativeMethods]::GetWindowRect($handle, [ref]$rect)
if (-not $ok) {{
    throw 'Failed to read window bounds.'
}}
[PSCustomObject]@{{
    left = $rect.Left
    top = $rect.Top
    right = $rect.Right
    bottom = $rect.Bottom
}} | ConvertTo-Json -Depth 2
"""
        raw = run_powershell(script)
        payload = json.loads(raw)
        return WindowRect(
            left=int(payload["left"]),
            top=int(payload["top"]),
            right=int(payload["right"]),
            bottom=int(payload["bottom"]),
        )

    def get_cursor_position(self) -> tuple[int, int]:
        script = f"""
{USER32_TYPES}
$point = New-Object POINT
$ok = [NativeMethods]::GetCursorPos([ref]$point)
if (-not $ok) {{
    throw 'Failed to read cursor position.'
}}
[PSCustomObject]@{{
    x = $point.X
    y = $point.Y
}} | ConvertTo-Json -Depth 2
"""
        raw = run_powershell(script)
        payload = json.loads(raw)
        return int(payload["x"]), int(payload["y"])

    def focus_window(self, handle: int) -> None:
        script = f"""
{USER32_TYPES}
$handle = [IntPtr]::new({handle})
[NativeMethods]::ShowWindowAsync($handle, 9) | Out-Null
Start-Sleep -Milliseconds 150
[NativeMethods]::SetForegroundWindow($handle) | Out-Null
"""
        run_powershell(script)

    def capture_window(self, handle: int, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        script = f"""
Add-Type -AssemblyName System.Drawing
{USER32_TYPES}
$target = {_ps_quote(str(output_path))}
$handle = [IntPtr]::new({handle})
$rect = New-Object RECT
[NativeMethods]::GetWindowRect($handle, [ref]$rect) | Out-Null
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
if ($width -le 0 -or $height -le 0) {{
    throw 'Window has invalid bounds.'
}}
$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
$bitmap.Save($target, [System.Drawing.Imaging.ImageFormat]::Bmp)
$graphics.Dispose()
$bitmap.Dispose()
Write-Output $target
"""
        run_powershell(script, timeout=40)
        return output_path

    def click_in_window(self, handle: int, offset_x: int, offset_y: int) -> None:
        script = f"""
{USER32_TYPES}
$handle = [IntPtr]::new({handle})
$rect = New-Object RECT
[NativeMethods]::ShowWindowAsync($handle, 9) | Out-Null
Start-Sleep -Milliseconds 150
[NativeMethods]::SetForegroundWindow($handle) | Out-Null
[NativeMethods]::GetWindowRect($handle, [ref]$rect) | Out-Null
$x = $rect.Left + {offset_x}
$y = $rect.Top + {offset_y}
[NativeMethods]::SetCursorPos($x, $y) | Out-Null
Start-Sleep -Milliseconds 120
[NativeMethods]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 40
[NativeMethods]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
"""
        run_powershell(script)

    def send_text(
        self,
        handle: int,
        text: str,
        click_x: int | None = None,
        click_y: int | None = None,
        submit: bool = True,
    ) -> None:
        click_block = ""
        if click_x is not None and click_y is not None:
            click_block = f"""
$rect = New-Object RECT
[NativeMethods]::GetWindowRect($handle, [ref]$rect) | Out-Null
$x = $rect.Left + {click_x}
$y = $rect.Top + {click_y}
[NativeMethods]::SetCursorPos($x, $y) | Out-Null
Start-Sleep -Milliseconds 120
[NativeMethods]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 40
[NativeMethods]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 180
"""
        submit_block = "[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')" if submit else ""
        script = f"""
Add-Type -AssemblyName System.Windows.Forms
{USER32_TYPES}
$handle = [IntPtr]::new({handle})
[NativeMethods]::ShowWindowAsync($handle, 9) | Out-Null
Start-Sleep -Milliseconds 150
[NativeMethods]::SetForegroundWindow($handle) | Out-Null
Start-Sleep -Milliseconds 150
{click_block}
$backup = ''
try {{
    $backup = Get-Clipboard -Raw
}} catch {{
    $backup = ''
}}
Set-Clipboard -Value {_ps_quote(text)}
Start-Sleep -Milliseconds 120
[System.Windows.Forms.SendKeys]::SendWait('^v')
Start-Sleep -Milliseconds 100
{submit_block}
Start-Sleep -Milliseconds 60
try {{
    Set-Clipboard -Value $backup
}} catch {{
}}
"""
        run_powershell(script, timeout=40)

    def inspect_automation_tree(self, window_title: str, limit: int = 40) -> list[dict[str, str]]:
        script = f"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty,
    {_ps_quote(window_title)}
)
$window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
if (-not $window) {{
    Write-Output '[]'
    exit 0
}}
$items = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$results = @()
$cap = [Math]::Min($items.Count, {limit})
for ($i = 0; $i -lt $cap; $i++) {{
    $item = $items.Item($i)
    $results += [PSCustomObject]@{{
        name = $item.Current.Name
        type = $item.Current.ControlType.ProgrammaticName
        automationId = $item.Current.AutomationId
    }}
}}
$results | ConvertTo-Json -Depth 3
"""
        raw = run_powershell(script)
        if not raw:
            return []
        payload = json.loads(raw)
        if isinstance(payload, dict):
            payload = [payload]
        return payload
