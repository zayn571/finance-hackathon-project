# RapDev Brex Weekly - unattended, DRAFT-ONLY run wrapper
# Registered as Windows Task "RapDev Brex Weekly" (Thursdays 9:00 AM).
# Runs the Brex Import skill headless via `claude -p`, logs JSON (incl total_cost_usd) to C:\logs,
# and emails a summary. It CANNOT post to QuickBooks or send anything externally — the dedicated
# settings file (.claude/brex-weekly-settings.json) denies those tools.

$ErrorActionPreference = "Stop"

$proj     = "G:\Shared drives\RapDev Finance - Claude\rapdev-finance-claude-skills"
$claude   = "C:\Users\zaynm\.local\bin\claude.exe"
$settings = Join-Path $proj ".claude\brex-weekly-settings.json"
$promptF  = Join-Path $proj "skills\brex-import\weekly-prompt.txt"


$stamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$log    = "C:\logs\brex-weekly-$stamp.json"
$errlog = "C:\logs\brex-weekly-$stamp.err.txt"

$cost = "n/a"; $status = "UNKNOWN"; $summary = ""

try {
    if (-not (Test-Path $proj)) { throw "Project drive not available: $proj (is Google Drive mounted in this session?)" }
    Set-Location $proj
    $prompt = Get-Content $promptF -Raw

    # Headless run. The dedicated settings file supplies dontAsk + allow/deny + Sonnet.
    $out = & $claude -p $prompt --output-format json --settings $settings --model sonnet
    $out | Out-File -FilePath $log -Encoding utf8

    $obj     = $out | ConvertFrom-Json
    $cost    = $obj.total_cost_usd
    $status  = if ($obj.is_error) { "ERROR" } else { "OK" }
    $summary = $obj.result
}
catch {
    $status  = "WRAPPER-FAILURE"
    $summary = $_.Exception.Message
    $_ | Out-File -FilePath $errlog -Encoding utf8
}

"[$(Get-Date)] Status=$status Cost=$cost Log=$log" | Out-File -Append "C:\logs\brex-weekly-notify.log"
