Param(
    [string]$PythonCommand
)

$ErrorActionPreference = "Stop"

function Resolve-Python {
    param([string]$Requested)

    if ($Requested) {
        return $Requested
    }

    foreach ($candidate in @("py", "python", "python3")) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            return $candidate
        }
    }

    throw "Python 3.9+ is required but was not found in PATH."
}

$python = Resolve-Python -Requested $PythonCommand

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$distDir = Join-Path $repoRoot "dist"
$installerRoot = Join-Path $distDir "installers"
$templateDir = Join-Path $repoRoot "installer"

if (Test-Path $distDir) {
    Remove-Item $distDir -Recurse -Force
}
New-Item -ItemType Directory -Path $installerRoot | Out-Null

Write-Host "Building wheel using $python..."
& $python -m build --outdir $distDir | Write-Host

$versionScript = @"
import pathlib, re, sys
text = pathlib.Path('pyproject.toml').read_text()
match = re.search(r"^version\s*=\s*\"([^\"]+)\"", text, re.MULTILINE)
if not match:
    sys.exit('Unable to determine version from pyproject.toml')
print(match.group(1))
"@

$version = (& $python -c $versionScript).Trim()
if (-not $version) {
    throw "Failed to resolve project version."
}

$packagePrefix = "ucm-color-admin-$version"
$targetDir = Join-Path $installerRoot $packagePrefix
New-Item -ItemType Directory -Path $targetDir | Out-Null

$wheel = Get-ChildItem -Path $distDir -Filter "ucm_color_admin-*.whl" | Select-Object -First 1
if (-not $wheel) {
    throw "Installer wheel not found in $distDir"
}

Copy-Item $wheel.FullName -Destination $targetDir
Copy-Item (Join-Path $templateDir "install.sh") -Destination $targetDir
Copy-Item (Join-Path $templateDir "install.ps1") -Destination $targetDir
Copy-Item (Join-Path $templateDir "README.txt") -Destination $targetDir

$archiveScript = @"
import pathlib, shutil, tarfile
installer_dir = pathlib.Path(r'$installerRoot')
prefix = '$packagePrefix'
target = installer_dir / prefix
tar_path = installer_dir / f"{prefix}-linux-macos.tar.gz"
with tarfile.open(tar_path, 'w:gz') as tar:
    tar.add(target, arcname=prefix)
shutil.make_archive(str(installer_dir / f"{prefix}-windows"), 'zip', root_dir=installer_dir, base_dir=prefix)
"@

& $python -c $archiveScript

Write-Host "Installer artifacts created under $installerRoot"
