# deploy/find_python.ps1: which Python MIA's installer can use (install.ps1).
#
# A Windows PC without Python still answers to "python": the Microsoft
# Store's placeholder prints "Python was not found..." and fails. Windows
# PowerShell 5.1 (what install.bat runs) turns that message into a
# stopping error when the script runs with -ErrorAction Stop (Zac's new PC,
# 2026-10-19), so each try here is fenced: a failing candidate is just "no".
#
# Too new is "no" as well: some of MIA's packages (libzim) have no build
# for a Python released after them (GitHub's Windows machines moved to
# one, 2026-10-24). The py launcher is asked for each version MIA knows
# works (best tested first), and Find-Python returns that python.exe's path.

function Test-Python($candidate) {
    if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) { return $false }
    $before = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $version = & $candidate -c "import sys; print((3, 10) <= sys.version_info[:2] <= (3, 14))" 2>$null
        return ($LASTEXITCODE -eq 0 -and "$version".Trim() -eq "True")
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $before
    }
}

function Find-Python {
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        foreach ($version in @("3.13", "3.12", "3.14", "3.11", "3.10")) {
            $before = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            try {
                $exe = & py "-$version" -c "import sys; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $exe -and (Test-Python "$exe".Trim())) { return "$exe".Trim() }
            } catch {
            } finally {
                $ErrorActionPreference = $before
            }
        }
    }
    foreach ($candidate in @("py", "python")) {
        if (Test-Python $candidate) { return $candidate }
    }
    # Installed a moment ago and not on this window's PATH yet: where python.org's installer puts it.
    foreach ($exe in @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "C:\Program Files\Python312\python.exe")) {
        if ((Test-Path $exe) -and (Test-Python $exe)) { return $exe }
    }
    return $null
}
