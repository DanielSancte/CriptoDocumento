[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$buildEnvironment = Join-Path $projectRoot ".venv-build"
$buildPython = Join-Path $buildEnvironment "Scripts\python.exe"
$requirementsLock = Join-Path $projectRoot "requirements.lock"
$specification = Join-Path $projectRoot "packaging\pdf-protector.spec"
$packagedExecutable = Join-Path $projectRoot "dist\ProtectorPDF\ProtectorPDF.exe"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Write-Host "==> $Description"
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Test-Python312X64 {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [string[]]$PrefixArguments = @()
    )

    & $Executable @PrefixArguments -c "import struct, sys; raise SystemExit(0 if sys.version_info[:3] == (3, 12, 2) and struct.calcsize('P') * 8 == 64 else 1)" 2>$null
    return $LASTEXITCODE -eq 0
}

$basePython = $null
$basePythonPrefix = @()
$pythonLauncher = Get-Command "py.exe" -ErrorAction SilentlyContinue
if ($null -ne $pythonLauncher -and (Test-Python312X64 $pythonLauncher.Source @("-3.12-64"))) {
    $basePython = $pythonLauncher.Source
    $basePythonPrefix = @("-3.12-64")
}

if ($null -eq $basePython) {
    $pythonCommand = Get-Command "python.exe" -ErrorAction SilentlyContinue
    if ($null -ne $pythonCommand -and (Test-Python312X64 $pythonCommand.Source)) {
        $basePython = $pythonCommand.Source
    }
}

if ($null -eq $basePython) {
    throw "Python 3.12.2 x64 is required to build ProtectorPDF."
}

Push-Location $projectRoot
try {
    Invoke-Checked "Create isolated build environment" $basePython @(
        $basePythonPrefix + @("-m", "venv", "--clear", $buildEnvironment)
    )
    Invoke-Checked "Install hash-locked dependencies" $buildPython @(
        "-m", "pip", "install", "--disable-pip-version-check", "--require-hashes",
        "--no-deps", "-r", $requirementsLock
    )
    Invoke-Checked "Run source test suite" $buildPython @(
        "-m", "pytest", "-v", "--ignore=tests/test_packaged_app.py",
        "--basetemp=.pytest-build-suite"
    )
    Invoke-Checked "Build onedir Windows distribution" $buildPython @(
        "-m", "PyInstaller", "--noconfirm", "--clean", $specification
    )
    if (-not (Test-Path -LiteralPath $packagedExecutable -PathType Leaf)) {
        throw "PyInstaller did not create $packagedExecutable."
    }
    Write-Host "==> Add user documentation to distribution"
    $distributionDirectory = Split-Path -Parent $packagedExecutable
    Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $distributionDirectory -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot "THIRD_PARTY_LICENSES.md") -Destination $distributionDirectory -Force
    Invoke-Checked "Run packaged application smoke test" $buildPython @(
        "-m", "pytest", "tests/test_packaged_app.py", "-v",
        "--basetemp=.pytest-build-packaged"
    )
    Write-Host "Build verified: $packagedExecutable"
}
finally {
    Pop-Location
}
