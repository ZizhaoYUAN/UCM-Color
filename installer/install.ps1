Param(
    [string]$InstallDir = "$env:LOCALAPPDATA\UCMColorAdmin"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "Python is required but was not found. Install Python 3.9+ and try again."
    }
    $python = "python"
} else {
    $python = "py"
}

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}

$venvDir = Join-Path $InstallDir "venv"
& $python -m venv $venvDir

$venvPython = Join-Path $venvDir "Scripts/python.exe"
& $venvPython -m pip install --upgrade pip | Out-Null

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$wheel = Get-ChildItem -Path $scriptDir -Filter "ucm_color_admin-*.whl" | Select-Object -First 1
if (-not $wheel) {
    Write-Error "Installer wheel not found."
}

& $venvPython -m pip install $wheel.FullName | Out-Null

$launcher = Join-Path $InstallDir "ucm-color-admin.ps1"
@"
param(
    [string[]]$Args
)

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
& "$scriptPath\venv\Scripts\ucm-color-admin.exe" @Args
"@ | Set-Content -Path $launcher -Encoding UTF8

Write-Host "Installation complete."
Write-Host "Use 'powershell -File $launcher run' to launch the service."
