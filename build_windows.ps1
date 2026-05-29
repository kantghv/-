$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Spec = Get-ChildItem -LiteralPath $Root -Filter "*.spec" | Select-Object -First 1
$Dist = Join-Path $Root "dist"
$Release = Join-Path $Root "release"

if ($null -eq $Spec) {
    throw "No PyInstaller spec file found."
}

Set-Location $Root
python -m PyInstaller --noconfirm --clean $Spec.FullName

$AppDir = Get-ChildItem -LiteralPath $Dist -Directory | Select-Object -First 1
if ($null -eq $AppDir) {
    throw "Build finished but no app folder was created."
}

$Exe = Get-ChildItem -LiteralPath $AppDir.FullName -Filter "*.exe" | Select-Object -First 1
if ($null -eq $Exe) {
    throw "Build finished but no exe was created."
}

$Notes = Join-Path $Root "release_notes.md"
if (Test-Path $Notes) {
    Copy-Item -LiteralPath $Notes -Destination (Join-Path $AppDir.FullName "release_notes.md") -Force
}

New-Item -ItemType Directory -Force -Path $Release | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd-HHmm"
$Zip = Join-Path $Release "YingXiaoAIWorkstation-$Stamp.zip"
if (Test-Path $Zip) {
    Remove-Item -LiteralPath $Zip -Force
}
Compress-Archive -Path $AppDir.FullName -DestinationPath $Zip -Force

Write-Host "BUILD_OK"
Write-Host $Exe.FullName
Write-Host $Zip
