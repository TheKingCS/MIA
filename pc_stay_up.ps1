# pc_stay_up.ps1: MIA comes back by itself after Windows restarts
# ============================================================================
#
# Windows Update restarts the computer at night and leaves it at the
# sign-in screen. MIA starts when you sign in, so until someone does, the
# phone and the cameras can't reach it. This:
#   1. asks Windows not to restart while you're signed in, and keeps
#      restarts out of 6 AM to midnight (Windows may still restart for an
#      urgent update; then step 2 brings MIA back);
#   2. signs you in by itself when the computer starts (Microsoft's
#      Sysinternals Autologon: you type your Windows password into it once,
#      and it keeps it encrypted), so MIA starts a minute after any restart.
#
# Run by setup_home_pc.ps1 (step 6), or on its own: double-click
# pc_stay_up.bat. Windows asks for permission (it changes system settings).
# Options: -Yes (don't ask), -DryRun (say what would happen; change nothing)

param(
    [switch]$Yes,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Note($text) { Write-Host "   $text" }
function Ask($question) {
    if ($Yes -or $DryRun) { return $true }
    $reply = Read-Host "   $question [Y/n]"
    return -not ($reply -match '^[nN]')
}

# Runs as administrator (one Windows permission prompt).
$updateSettings = @'
$au = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
New-Item -Path $au -Force | Out-Null
Set-ItemProperty -Path $au -Name NoAutoRebootWithLoggedOnUsers -Type DWord -Value 1
$ux = "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"
New-Item -Path $ux -Force | Out-Null
Set-ItemProperty -Path $ux -Name SmartActiveHoursState -Type DWord -Value 0
Set-ItemProperty -Path $ux -Name ActiveHoursStart -Type DWord -Value 6
Set-ItemProperty -Path $ux -Name ActiveHoursEnd -Type DWord -Value 0
'@

if (Ask "Ask Windows Update not to restart while you're signed in, and never between 6 AM and midnight?") {
    if ($DryRun) { Note "(dry run) would: set NoAutoRebootWithLoggedOnUsers and active hours 6:00-0:00" }
    else {
        $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($updateSettings))
        $run = Start-Process powershell -Verb RunAs -Wait -PassThru `
            -ArgumentList "-NoProfile", "-EncodedCommand", $encoded
        if ($run.ExitCode -eq 0) { Note "Windows Update now restarts only between midnight and 6 AM, and not while you're signed in." }
        else { Note "That didn't go through (Windows said no?). Run this again to retry." }
    }
}

if (Ask "Sign in to Windows by itself when the computer starts, so MIA comes back after a restart?") {
    Note "Anyone at this computer's keyboard will get in without your Windows password."
    Note "MIA itself still asks for your MIA password on its lock screen."
    if ($DryRun) { Note "(dry run) would: winget install Microsoft.Sysinternals.Autologon, then open it" }
    else {
        $exe = Get-Command autologon64, autologon -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $exe) {
            winget install --id Microsoft.Sysinternals.Autologon -e --accept-source-agreements --accept-package-agreements
            $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                        [Environment]::GetEnvironmentVariable("Path", "User")
            $exe = Get-Command autologon64, autologon -ErrorAction SilentlyContinue | Select-Object -First 1
        }
        if ($exe) {
            Note "Autologon opens now: check the user name, type your Windows password, press Enable."
            Note "(Signed in with a Microsoft account? Use its email as the user name and its password, not your PIN."
            Note " If Enable doesn't stick: Settings -> Accounts -> Sign-in options -> turn off"
            Note " 'For improved security, only allow Windows Hello sign-in', then try again.)"
            Start-Process $exe.Source -Wait
        } else { Note "Autologon didn't install. Get it from learn.microsoft.com/sysinternals/downloads/autologon." }
    }
}
