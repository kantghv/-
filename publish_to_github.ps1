param(
    [Parameter(Mandatory = $true)]
    [string]$RemoteUrl
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath ".git")) {
    git init -b main
}

git status -sb
git remote remove origin 2>$null
git remote add origin $RemoteUrl
git push -u origin main

Write-Host ""
Write-Host "Published to GitHub: $RemoteUrl"
