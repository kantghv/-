[CmdletBinding()]
param(
    [string]$InstallDir
)

$ErrorActionPreference = "Stop"

function New-UnicodeString {
    param([int[]]$CodePoints)
    $chars = foreach ($point in $CodePoints) { [char]$point }
    return [string]::Concat($chars)
}

$AppName = "$(New-UnicodeString @(0x6620, 0x6548))AI$(New-UnicodeString @(0x5DE5, 0x4F5C, 0x7AD9))"
$Version = "0.4.9"
$ExeName = "$AppName.exe"

function Get-DefaultInstallDir {
    if (Test-Path -LiteralPath "D:\") {
        return (Join-Path "D:\" $AppName)
    }
    return (Join-Path $env:LOCALAPPDATA "Programs\$AppName")
}

function Resolve-SourceApp {
    param([string]$Root)

    $candidates = @(
        (Join-Path (Join-Path $Root "dist") $AppName),
        (Join-Path (Join-Path $Root "dist_043") $AppName),
        (Join-Path (Join-Path $Root "dist_042") $AppName),
        (Join-Path $Root $AppName)
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $candidate $ExeName)) {
            return $candidate
        }
    }

    throw "No installable app folder found next to this script."
}

function New-AppShortcut {
    param(
        [string]$ShortcutPath,
        [string]$TargetPath,
        [string]$WorkingDirectory
    )

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.WorkingDirectory = $WorkingDirectory
    $shortcut.IconLocation = $TargetPath
    $shortcut.Description = "$AppName $Version"
    $shortcut.Save()
}

if (-not $InstallDir) {
    $InstallDir = Get-DefaultInstallDir
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceApp = Resolve-SourceApp -Root $scriptRoot
$installParent = Split-Path -Parent $InstallDir
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "$InstallDir.backup_$timestamp"

if ($installParent -and -not (Test-Path -LiteralPath $installParent)) {
    New-Item -ItemType Directory -Force -Path $installParent | Out-Null
}

if (Test-Path -LiteralPath $InstallDir) {
    Move-Item -LiteralPath $InstallDir -Destination $backupDir
}

Copy-Item -LiteralPath $sourceApp -Destination $InstallDir -Recurse -Force

$targetExe = Join-Path $InstallDir $ExeName
$desktopDir = [Environment]::GetFolderPath("Desktop")
$programsDir = [Environment]::GetFolderPath("Programs")
$startMenuDir = Join-Path $programsDir $AppName
$desktopShortcut = Join-Path $desktopDir "$AppName.lnk"
$startShortcut = Join-Path $startMenuDir "$AppName.lnk"

New-Item -ItemType Directory -Force -Path $startMenuDir | Out-Null
New-AppShortcut -ShortcutPath $desktopShortcut -TargetPath $targetExe -WorkingDirectory $InstallDir
New-AppShortcut -ShortcutPath $startShortcut -TargetPath $targetExe -WorkingDirectory $InstallDir

$uninstallScript = @"
`$ErrorActionPreference = "Stop"
`$appName = "$AppName"
`$installDir = "$InstallDir"
`$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "`$appName.lnk"
`$startMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) `$appName
if (Test-Path -LiteralPath `$desktopShortcut) { Remove-Item -LiteralPath `$desktopShortcut -Force }
if (Test-Path -LiteralPath `$startMenuDir) { Remove-Item -LiteralPath `$startMenuDir -Recurse -Force }
Write-Host "Shortcuts removed."
Write-Host "Program files remain here: `$installDir"
"@

$uninstallPath = Join-Path $InstallDir "uninstall_windows.ps1"
Set-Content -LiteralPath $uninstallPath -Value $uninstallScript -Encoding UTF8

$installInfo = [ordered]@{
    app = $AppName
    version = $Version
    installed_at = (Get-Date).ToString("s")
    install_dir = $InstallDir
    source_dir = $sourceApp
    desktop_shortcut = $desktopShortcut
    start_menu_shortcut = $startShortcut
    backup_dir = $(if (Test-Path -LiteralPath $backupDir) { $backupDir } else { $null })
}

$installInfo | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $InstallDir "install-info.json") -Encoding UTF8

Write-Host ""
Write-Host "$AppName $Version installed."
Write-Host "Install dir: $InstallDir"
Write-Host "Desktop shortcut: $desktopShortcut"
Write-Host "Start menu shortcut: $startShortcut"
if (Test-Path -LiteralPath $backupDir) {
    Write-Host "Previous version backup: $backupDir"
}
