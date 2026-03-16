# avilonROBOTICS Content Team — Setup Script
# Run this on any new PC after cloning the repo
# Usage: powershell -File setup.ps1

$base = "D:\Claude Agent"
$claudeAgentsDir = "$env:USERPROFILE\.claude\agents"

Write-Host ""
Write-Host "  avilonROBOTICS Content Team — Setup" -ForegroundColor Cyan
Write-Host "  =====================================" -ForegroundColor Cyan
Write-Host ""

# 1. Create required folders
Write-Host "  [1/5] Creating folders..." -ForegroundColor Yellow
$folders = @(
    "$base\drafts",
    "$base\reports",
    "$base\plans",
    "$base\history",
    "$base\Log",
    "$base\memory"
)
foreach ($f in $folders) {
    if (!(Test-Path $f)) {
        New-Item -ItemType Directory -Path $f -Force | Out-Null
        Write-Host "       Created: $f" -ForegroundColor Gray
    } else {
        Write-Host "       OK: $f" -ForegroundColor DarkGray
    }
}

# 2. Init history file if missing
if (!(Test-Path "$base\history\posts.json")) {
    "[]" | Set-Content "$base\history\posts.json" -Encoding UTF8
    Write-Host "  [2/5] Created history/posts.json" -ForegroundColor Yellow
} else {
    Write-Host "  [2/5] history/posts.json OK" -ForegroundColor DarkGray
}

# 3. Install agents to ~/.claude/agents/
Write-Host "  [3/5] Installing agents to ~/.claude/agents/..." -ForegroundColor Yellow
if (!(Test-Path $claudeAgentsDir)) {
    New-Item -ItemType Directory -Path $claudeAgentsDir -Force | Out-Null
}
$agents = @(
    "trend-monitor.md",
    "editor-in-chief.md",
    "tech-writer.md",
    "ad-writer.md",
    "proofreader.md"
)
foreach ($agent in $agents) {
    $src = "$base\Agents\$agent"
    $dst = "$claudeAgentsDir\$agent"
    if (Test-Path $src) {
        Copy-Item $src $dst -Force
        Write-Host "       Installed: $agent" -ForegroundColor Gray
    } else {
        Write-Host "       MISSING: $src" -ForegroundColor Red
    }
}

# 4. Install Python dependencies
Write-Host "  [4/5] Installing Python dependencies..." -ForegroundColor Yellow
$pipResult = python3 -m pip install flask --quiet 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "       Flask installed OK" -ForegroundColor Gray
} else {
    Write-Host "       Warning: pip install failed — install Flask manually" -ForegroundColor Red
}

# 5. Register Task Scheduler (optional)
Write-Host "  [5/5] Task Scheduler (AvilonTrendMonitor)..." -ForegroundColor Yellow
$taskExists = Get-ScheduledTask -TaskName "AvilonTrendMonitor" -ErrorAction SilentlyContinue
if ($taskExists) {
    Write-Host "       Already registered — skipping" -ForegroundColor DarkGray
} else {
    try {
        $claudeExe = "$env:USERPROFILE\.local\bin\claude.exe"
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NonInteractive -File `"$base\trend-monitor-run.ps1`""
        $trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Hours 6) -Once -At (Get-Date)
        $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2)
        Register-ScheduledTask -TaskName "AvilonTrendMonitor" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null
        Write-Host "       Registered — runs every 6 hours" -ForegroundColor Gray
    } catch {
        Write-Host "       Warning: Task Scheduler registration failed — register manually" -ForegroundColor Red
    }
}

# Done
Write-Host ""
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "  1. Start dashboard:  python3 `"$base\dashboard\server.py`""
Write-Host "  2. Open dashboard:   http://localhost:5050"
Write-Host "  3. Public URL:       Run cloudflared, check reports\tunnel-err.log"
Write-Host "  4. Open Claude Code: cd `"$base`" && claude"
Write-Host ""
