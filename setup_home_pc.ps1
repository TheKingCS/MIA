# setup_home_pc.ps1: make this computer MIA's home base (DEC-0022, DEC-0033)
# ============================================================================
#
# Double-click setup_home_pc.bat (it runs this). It asks before each step,
# is safe to run again, and ends with a readiness check (tools/pc_check.py)
# that says exactly what's left.
#
#   1. MIA itself (runs install.bat's installer first if MIA isn't installed).
#   2. The brain: Ollama on the graphics card, with qwen2.5:14b
#      (and qwen2.5:32b to compare, if you want).
#   3. MIA's settings: that model, and Phone Access on (only on this
#      computer: the phone comes in through Tailscale, nothing is opened).
#   4. ffmpeg, for cameras that only stream video (Tapo, Wyze).
#   5. Tailscale: sign in, then serve MIA to your own devices only.
#   6. MIA starts when you sign in to Windows; the computer doesn't sleep
#      while plugged in (so the phone and the cameras always find it), and
#      after a Windows Update restart it signs in and MIA comes back
#      (pc_stay_up.ps1).
#   7. The model comparison (optional, 30-60 minutes): which model MIA's
#      home computer should run.
#   8. The readiness check.
#
# Options: -Yes (don't ask), -DryRun (say what would happen; change nothing)

param(
    [switch]$Yes,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$MiaDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $MiaDir
$Port = 8765
$Model = "qwen2.5:14b"
$BigModel = "qwen2.5:32b"

function Step($text) { Write-Host "`n== $text ==" -ForegroundColor Cyan }
function Note($text) { Write-Host "   $text" }
function Ask($question) {
    if ($Yes -or $DryRun) { return $true }
    $reply = Read-Host "   $question [Y/n]"
    return -not ($reply -match '^[nN]')
}
function Have($command) { return [bool](Get-Command $command -ErrorAction SilentlyContinue) }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}
function Do-It($what, [scriptblock]$action) {
    if ($DryRun) { Note "(dry run) would: $what"; return }
    & $action
}
function Winget-Install($id, $what) {
    if (-not (Have "winget")) { Note "winget isn't available. Install $what yourself, then run this again."; return }
    Do-It "winget install $id" { winget install --id $id -e --accept-source-agreements --accept-package-agreements; Refresh-Path }
}
function Tailscale-Exe {
    if (Have "tailscale") { return "tailscale" }
    $guess = "C:\Program Files\Tailscale\tailscale.exe"
    if (Test-Path $guess) { return $guess }
    return $null
}

Write-Host "MIA: setting up this computer as MIA's home base"
Write-Host "Folder: $MiaDir"
if ($DryRun) { Write-Host "Dry run: nothing will be installed or changed." -ForegroundColor Yellow }
$venvPython = Join-Path $MiaDir ".venv\Scripts\python.exe"
# The comparison already ran here, so the model is picked: skip the 32b and the comparison.
$compared = Test-Path (Join-Path $MiaDir "pc-check\models.json")

# ------------------------------------------------------------ 1. MIA
Step "1/8 MIA"
if (Test-Path $venvPython) { Note "MIA is installed." }
else {
    Note "MIA isn't installed yet: running its installer first."
    Do-It "run install.ps1" {
        $installArgs = @()
        if ($Yes) { $installArgs += "-Yes" }
        & (Join-Path $MiaDir "install.ps1") @installArgs
    }
}

# ------------------------------------------------------------ 2. the brain
Step "2/8 The brain (Ollama on the graphics card)"
if (Have "ollama") { Note "Ollama is installed." }
elseif (Ask "Install Ollama? (it runs the model on your Radeon; nothing leaves this computer)") {
    Winget-Install "Ollama.Ollama" "Ollama (ollama.com)"
}
if (Have "ollama") {
    Note "Getting $Model (about 9 GB, one time)..."
    Do-It "ollama pull $Model" { ollama pull $Model }
    if (-not $compared -and (Ask "Also get $BigModel (about 19 GB) so MIA can compare the two?")) {
        Do-It "ollama pull $BigModel" { ollama pull $BigModel }
    }
} elseif (-not $DryRun) { Note "Ollama isn't on this computer yet; run this again after installing it." }

# ------------------------------------------------------------ 3. settings
Step "3/8 MIA's settings: the model and Phone Access"
$settings = @"
from core.config_manager import ConfigManager
c = ConfigManager()
c.set('llm.model', '$Model')
c.set('server.enabled', True)
c.set('server.host', '127.0.0.1')
c.set('server.port', $Port)
c.save()
print('   MIA will use $Model; Phone Access is on (port $Port, this computer only).')
"@
if (Test-Path $venvPython) { Do-It "set llm.model and server.enabled" { & $venvPython -c $settings } }
else { Note "(MIA isn't installed, so this waits for the next run.)" }
Note "Your account needs a password for the phone: MIA -> Settings -> Change Password (the check at the end says if it's missing)."

# ------------------------------------------------------------ 4. cameras
Step "4/8 Cameras that stream (ffmpeg)"
if (Have "ffmpeg") { Note "ffmpeg is installed." }
elseif (Ask "Install ffmpeg? (only needed for Tapo / Wyze cameras; Reolink, Amcrest and Hikvision don't need it)") {
    Winget-Install "Gyan.FFmpeg" "ffmpeg (ffmpeg.org)"
}

# ------------------------------------------------------------ 5. Tailscale
Step "5/8 Tailscale (your phone reaches MIA from anywhere, and nobody else can)"
$ts = Tailscale-Exe
if (-not $ts -and (Ask "Install Tailscale?")) {
    Winget-Install "Tailscale.Tailscale" "Tailscale (tailscale.com/download)"
    $ts = Tailscale-Exe
}
if ($ts) {
    Note "Signing in: a browser window opens; use the same account you'll use on the phone."
    Do-It "tailscale up" { & $ts up }
    Do-It "tailscale serve --bg http://127.0.0.1:$Port" { & $ts serve --bg "http://127.0.0.1:$Port" }
    if (-not $DryRun) {
        $status = (& $ts serve status) -join "`n"
        New-Item -ItemType Directory -Force -Path (Join-Path $MiaDir "pc-check") | Out-Null
        $status | Set-Content -Encoding UTF8 (Join-Path $MiaDir "pc-check\tailscale.txt")
        $url = [regex]::Match($status, 'https://[^\s]+\.ts\.net').Value
        if ($url) {
            Write-Host "`n   The phone's address for MIA:  $url" -ForegroundColor Green
            Note "(saved in pc-check\tailscale.txt) On the phone: Settings -> Home Computer -> Link, with this address."
        } else { Note "Tailscale says: $status" }
    }
} elseif (-not $DryRun) { Note "Tailscale isn't installed yet; run this again after installing it." }

# ------------------------------------------------------------ 6. always there
Step "6/8 Always there for the phone and the cameras"
if (Ask "Start MIA when you sign in to Windows?") {
    $startup = Join-Path ([Environment]::GetFolderPath("Startup")) "MIA.lnk"
    Do-It "add $startup" {
        $shell = New-Object -ComObject WScript.Shell
        $link = $shell.CreateShortcut($startup)
        $link.TargetPath = (Join-Path $MiaDir ".venv\Scripts\pythonw.exe")
        $link.Arguments = "`"$(Join-Path $MiaDir 'main.py')`""
        $link.WorkingDirectory = $MiaDir
        $link.IconLocation = (Join-Path $MiaDir "assets\mia_icon.ico")
        $link.Description = "MIA, your offline assistant"
        $link.Save()
        Note "MIA starts when you sign in."
    }
}
if (Ask "Keep this computer awake while it's plugged in? (the screen can still turn off)") {
    Do-It "powercfg: never sleep on AC power" { powercfg /change standby-timeout-ac 0; Note "It won't sleep while plugged in." }
}
$stayUpArgs = @()
if ($Yes) { $stayUpArgs += "-Yes" }
if ($DryRun) { $stayUpArgs += "-DryRun" }
& (Join-Path $MiaDir "pc_stay_up.ps1") @stayUpArgs

# ------------------------------------------------------------ 7. which model
Step "7/8 Which model is best here (optional, 30-60 minutes)"
if ($compared) { Note "Already done (pc-check\models.md); MIA uses $Model." }
elseif ((Test-Path $venvPython) -and (Have "ollama") -and (Ask "Run the model comparison now? (MIA's test questions on each model)")) {
    Do-It "tools\pc_model_check.py" {
        & $venvPython tools\pc_model_check.py
        $result = Join-Path $MiaDir "pc-check\models.json"
        if (Test-Path $result) {
            $best = (Get-Content $result -Raw | ConvertFrom-Json).recommended
            if ($best -and $best -ne $Model -and (Ask "Switch MIA to $best, the recommended model?")) {
                & $venvPython -c "from core.config_manager import ConfigManager; c = ConfigManager(); c.set('llm.model', '$best'); c.save()"
                Note "MIA will use $best."
            }
            Note "The results are in pc-check\models.md: tell Claude they're there (or paste them)."
        }
    }
} else { Note "Skipped. Run it any time: .venv\Scripts\python tools\pc_model_check.py" }

# ------------------------------------------------------------ 8. check
Step "8/8 Is everything ready?"
if (Test-Path $venvPython) {
    if ($DryRun) { Note "(dry run) would: run tools\pc_check.py" }
    else { & $venvPython tools\pc_check.py }
} else { Note "Install MIA first (install.bat), then run this again." }

Write-Host "`nNext: restart MIA (so Phone Access starts), then on the phone: Settings -> Home Computer -> Link."
exit 0
