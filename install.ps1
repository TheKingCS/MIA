# install.ps1: MIA's installer for Windows
# ========================================
#
# Double-click install.bat (it runs this). It asks before each big step
# and is safe to run again.
#
#   1. Python 3.12, Ollama (MIA's brain) and Tesseract (reading photos),
#      with winget, Windows' own app installer, if they're missing.
#   2. MIA's Python packages, in a private .venv folder.
#   3. Voice models, the AI model and a setup check (deploy/finish_install.py).
#   4. A "MIA" shortcut on the desktop and in the Start menu.
#
# Options: -Yes (don't ask), -NoOllama, -NoVoice, -NoTesseract

param(
    [switch]$Yes,
    [switch]$NoOllama,
    [switch]$NoVoice,
    [switch]$NoTesseract
)

$ErrorActionPreference = "Stop"
$MiaDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $MiaDir

function Step($text) { Write-Host "`n== $text ==" -ForegroundColor Cyan }
function Note($text) { Write-Host "   $text" }
function Ask($question) {
    if ($Yes) { return $true }
    $reply = Read-Host "   $question [Y/n]"
    return -not ($reply -match '^[nN]')
}
function Have($command) { return [bool](Get-Command $command -ErrorAction SilentlyContinue) }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}
function Winget-Install($id, $what) {
    if (-not (Have "winget")) {
        Note "winget isn't available. Install $what yourself, then run this again."
        return $false
    }
    winget install --id $id -e --accept-source-agreements --accept-package-agreements
    Refresh-Path
    return $true
}

Write-Host "MIA installer"
Write-Host "Folder: $MiaDir"

# ------------------------------------------------------------ 1. tools
Step "1/4 Python, Ollama and Tesseract"
$python = $null
foreach ($candidate in @("py", "python")) {
    if (Have $candidate) {
        $version = & $candidate -c "import sys; print(sys.version_info >= (3, 10))" 2>$null
        if ($version -eq "True") { $python = $candidate; break }
    }
}
if (-not $python) {
    if (Ask "Python 3.10 or newer isn't installed. Install Python 3.12?") {
        Winget-Install "Python.Python.3.12" "Python 3.12 (python.org)" | Out-Null
        foreach ($candidate in @("py", "python")) { if (Have $candidate) { $python = $candidate; break } }
    }
    if (-not $python) { Write-Host "MIA needs Python. Install it from python.org, then run this again."; exit 1 }
}
Note "Python: $python"

if ($NoOllama) { Note "Ollama skipped." }
elseif (Have "ollama") { Note "Ollama is installed." }
elseif (Ask "Install Ollama, MIA's brain? (runs on this computer; nothing leaves it)") {
    Winget-Install "Ollama.Ollama" "Ollama (ollama.com)" | Out-Null
}

$tesseract = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if ($NoTesseract) { Note "Tesseract skipped." }
elseif ((Have "tesseract") -or (Test-Path $tesseract)) { Note "Tesseract is installed." }
elseif (Ask "Install Tesseract, so MIA can read photos of receipts and scans?") {
    Winget-Install "UB-Mannheim.TesseractOCR" "Tesseract (github.com/UB-Mannheim/tesseract)" | Out-Null
}

# ------------------------------------------------------------ 2. packages
Step "2/4 MIA's Python packages"
$venvPython = Join-Path $MiaDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) { & $python -m venv .venv }
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "Installing packages failed; check your internet and run this again."; exit 1 }

# ------------------------------------------------------------ 3. finish
Step "3/4 Voice, model and setup check"
$finishArgs = @("deploy\finish_install.py", "--no-shortcut")
if ($NoVoice) { $finishArgs += "--no-voice" }
if ($NoOllama) { $finishArgs += "--no-model" }
& $venvPython @finishArgs

# ------------------------------------------------------------ 4. shortcut
Step "4/4 Shortcut"
$pythonw = Join-Path $MiaDir ".venv\Scripts\pythonw.exe"
$shell = New-Object -ComObject WScript.Shell
foreach ($folder in @([Environment]::GetFolderPath("Desktop"), [Environment]::GetFolderPath("Programs"))) {
    $link = $shell.CreateShortcut((Join-Path $folder "MIA.lnk"))
    $link.TargetPath = $pythonw
    $link.Arguments = "`"$(Join-Path $MiaDir 'main.py')`""
    $link.WorkingDirectory = $MiaDir
    $link.IconLocation = (Join-Path $MiaDir "assets\mia_icon.ico")
    $link.Description = "MIA, your offline assistant"
    $link.Save()
    Note "Shortcut: $(Join-Path $folder 'MIA.lnk')"
}

Write-Host "`nDone. Start MIA from the MIA shortcut on your desktop or Start menu."
Write-Host "Run install.bat again any time to finish or update anything."
# The setup check's warnings (e.g. Ollama not installed yet) are advice,
# not a failed install: finishing here means everything above worked.
exit 0
