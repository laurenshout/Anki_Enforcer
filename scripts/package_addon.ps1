param(
    [string]$AddonName = "focus_enforcer",
    [string]$Version = "dev"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist"
$safeVersion = ($Version -replace "[^A-Za-z0-9._-]", "_")
$stagingRoot = Join-Path $dist ("_staging_" + $safeVersion)
$stagingAddonDir = Join-Path $stagingRoot $AddonName
$archiveName = "$AddonName-$Version.ankiaddon"
$archivePath = Join-Path $dist $archiveName
$zipPath = Join-Path $dist "$AddonName-$Version.zip"

function Reset-Dir([string]$Path) {
    if (Test-Path $Path) {
        Remove-Item -Recurse -Force $Path
    }
    New-Item -ItemType Directory -Path $Path | Out-Null
}

if (-not (Test-Path $dist)) {
    New-Item -ItemType Directory -Path $dist | Out-Null
}
Reset-Dir $stagingRoot
New-Item -ItemType Directory -Path $stagingAddonDir | Out-Null

$includePaths = @(
    "__init__.py",
    "anki_enforcer",
    "config.json",
    "scripts/anki_autostart.ps1",
    "assets",
    "README.md",
    "AUTO_START_WINDOWS.md"
)

foreach ($item in $includePaths) {
    $src = Join-Path $root $item
    if (-not (Test-Path $src)) {
        throw "Missing required path: $item"
    }
    Copy-Item -Path $src -Destination $stagingAddonDir -Recurse -Force
}

if (Test-Path $archivePath) {
    Remove-Item -Force $archivePath
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

Compress-Archive -Path $stagingAddonDir -DestinationPath $zipPath -Force
Move-Item -Path $zipPath -Destination $archivePath -Force
Write-Host "Created package: $archivePath"
