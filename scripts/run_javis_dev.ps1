param(
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$DesktopShell = Join-Path $RepoRoot "desktop-shell"
$ApiPort = 8765
$WebPort = 5173
$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

function Test-PortOpen {
  param(
    [int]$Port
  )

  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
    $ready = $async.AsyncWaitHandle.WaitOne(250)
    if (-not $ready) {
      $client.Close()
      return $false
    }
    $client.EndConnect($async)
    $client.Close()
    return $true
  } catch {
    return $false
  }
}

function Wait-PortOpen {
  param(
    [int]$Port,
    [int]$TimeoutSeconds = 20
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-PortOpen -Port $Port) {
      return $true
    }
    Start-Sleep -Milliseconds 350
  }

  return $false
}

function Start-WorkerWindow {
  param(
    [string]$Name,
    [string]$Workdir,
    [string]$Command
  )

  $escapedWorkdir = $Workdir.Replace("'", "''")
  $launchCommand = "Set-Location -LiteralPath '$escapedWorkdir'; $Command"

  if ($DryRun) {
    Write-Host "[dry-run] start $Name => $launchCommand"
    return
  }

  Start-Process -FilePath $PowerShellExe -ArgumentList @(
    "-NoExit",
    "-Command",
    $launchCommand
  ) | Out-Null
}

Write-Host ""
Write-Host "== javis dev launcher =="
Write-Host "repo: $RepoRoot"
Write-Host ""

if (-not (Test-PortOpen -Port $ApiPort)) {
  Write-Host "API server not detected on $ApiPort. Starting new window..."
  Start-WorkerWindow -Name "api" -Workdir $RepoRoot -Command "python -m app.api.server"
  if (-not $DryRun) {
    if (-not (Wait-PortOpen -Port $ApiPort -TimeoutSeconds 20)) {
      throw "API server did not open port $ApiPort in time."
    }
  }
} else {
  Write-Host "API server already running on $ApiPort."
}

if (-not (Test-PortOpen -Port $WebPort)) {
  Write-Host "Vite dev server not detected on $WebPort. Starting new window..."
  Start-WorkerWindow -Name "web" -Workdir $DesktopShell -Command "npm run dev:web"
  if (-not $DryRun) {
    if (-not (Wait-PortOpen -Port $WebPort -TimeoutSeconds 25)) {
      throw "Vite dev server did not open port $WebPort in time."
    }
  }
} else {
  Write-Host "Vite dev server already running on $WebPort."
}

Write-Host "Launching Electron shell..."

if ($DryRun) {
  Write-Host "[dry-run] cd `"$DesktopShell`""
  Write-Host "[dry-run] npm run dev:shell"
  exit 0
}

Set-Location -LiteralPath $DesktopShell
npm run dev:shell
