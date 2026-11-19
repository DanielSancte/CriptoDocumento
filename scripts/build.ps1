[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$buildEnvironment = Join-Path $projectRoot ".venv-build"
$buildPython = Join-Path $buildEnvironment "Scripts\python.exe"
$requirementsLock = Join-Path $projectRoot "requirements.lock"
$specification = Join-Path $projectRoot "packaging\pdf-protector.spec"
$licenseMaterials = Join-Path $projectRoot "packaging\licenses"
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

function Copy-RequiredFile {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
        throw "Required license material is missing: $Source"
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Copy-RequiredDirectory {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        throw "Required license directory is missing: $Source"
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
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
    Write-Host "==> Add user documentation and license materials to distribution"
    $distributionDirectory = Split-Path -Parent $packagedExecutable
    Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $distributionDirectory -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot "THIRD_PARTY_LICENSES.md") -Destination $distributionDirectory -Force

    $licenseDirectory = Join-Path $distributionDirectory "LICENSES"
    if (Test-Path -LiteralPath $licenseDirectory) {
        throw "PyInstaller left an unexpected stale LICENSES directory: $licenseDirectory"
    }
    New-Item -ItemType Directory -Path $licenseDirectory | Out-Null

    Copy-RequiredFile `
        (Join-Path $licenseMaterials "GNU-GPL-3.0.txt") `
        (Join-Path $licenseDirectory "GNU-GPL-3.0.txt")
    Copy-RequiredFile `
        (Join-Path $licenseMaterials "GNU-LGPL-3.0.txt") `
        (Join-Path $licenseDirectory "GNU-LGPL-3.0.txt")
    Copy-RequiredFile `
        (Join-Path $licenseMaterials "Qt-PySide6-SOURCE-INFORMATION.txt") `
        (Join-Path $licenseDirectory "Qt-PySide6-SOURCE-INFORMATION.txt")

    $pythonBasePrefix = (& $buildPython -c "import sys; print(sys.base_prefix)").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($pythonBasePrefix)) {
        throw "Could not locate the CPython license directory."
    }
    $sitePackages = (& $buildPython -c "import sysconfig; print(sysconfig.get_path('purelib'))").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($sitePackages)) {
        throw "Could not locate build-environment package licenses."
    }

    Copy-RequiredFile `
        (Join-Path $pythonBasePrefix "LICENSE.txt") `
        (Join-Path $licenseDirectory "CPython-3.12.2-LICENSE.txt")
    Copy-RequiredFile `
        (Join-Path $sitePackages "pillow-13.0.0.dist-info\licenses\LICENSE") `
        (Join-Path $licenseDirectory "Pillow-13.0.0-LICENSE.txt")
    Copy-RequiredFile `
        (Join-Path $sitePackages "lxml-6.1.3.dist-info\licenses\LICENSE.txt") `
        (Join-Path $licenseDirectory "lxml-6.1.3-LICENSE.txt")
    Copy-RequiredFile `
        (Join-Path $sitePackages "lxml-6.1.3.dist-info\licenses\LICENSES.txt") `
        (Join-Path $licenseDirectory "lxml-6.1.3-THIRD-PARTY-LICENSES.txt")
    Copy-RequiredFile `
        (Join-Path $sitePackages "typing_extensions-4.16.0.dist-info\licenses\LICENSE") `
        (Join-Path $licenseDirectory "typing-extensions-4.16.0-LICENSE.txt")
    Copy-RequiredFile `
        (Join-Path $sitePackages "pyinstaller-6.22.3.dist-info\licenses\COPYING.txt") `
        (Join-Path $licenseDirectory "PyInstaller-6.22.3-COPYING.txt")
    Copy-RequiredDirectory `
        (Join-Path $sitePackages "packaging-26.3.dist-info\licenses") `
        (Join-Path $licenseDirectory "packaging-26.3")
    Copy-RequiredDirectory `
        (Join-Path $sitePackages "pikepdf-10.18.2.dist-info\licenses") `
        (Join-Path $licenseDirectory "pikepdf-10.18.2")

    Invoke-Checked "Run packaged application smoke test" $buildPython @(
        "-m", "pytest", "tests/test_packaged_app.py", "-v",
        "--basetemp=.pytest-build-packaged"
    )
    Write-Host "Build verified: $packagedExecutable"
}
finally {
    Pop-Location
}
