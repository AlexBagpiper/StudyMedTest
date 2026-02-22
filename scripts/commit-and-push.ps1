# Быстрый коммит и пуш. Использование: ./scripts/commit-and-push.ps1 "сообщение коммита"
param([string]$Message = "update")
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
git add -A
$status = git status --porcelain
if (-not $status) { Write-Host "Nothing to commit."; exit 0 }
git commit -m $Message
git push
