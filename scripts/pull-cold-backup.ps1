# Скачать latest-снимок с VPS на локальный HDD (холодное хранилище).
#
#   .\scripts\pull-cold-backup.ps1 -Dest "D:\Archive\StudyMedTest"
#   .\scripts\pull-cold-backup.ps1 -Dest "E:\backups" -Host 151.248.126.120 -User medtest
#
# Требует: OpenSSH (scp) или WSL rsync. Ключ SSH — без пароля в скрипте.

param(
  [Parameter(Mandatory = $true)]
  [string] $Dest,

  [string] $VpsHost = "151.248.126.120",
  [string] $User = "medtest",
  [string] $RemotePath = "/home/medtest/backups/cold-staging/latest",
  [string] $IdentityFile = "$PSScriptRoot\..\RSA\rsa"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Dest)) {
  New-Item -ItemType Directory -Path $Dest -Force | Out-Null
}

$stamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$localDir = Join-Path $Dest "prod-$stamp"
New-Item -ItemType Directory -Path $localDir -Force | Out-Null

$sshArgs = @("-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new")
if (Test-Path $IdentityFile) {
  $sshArgs += @("-i", (Resolve-Path $IdentityFile).Path)
}

$remote = "${User}@${VpsHost}:${RemotePath}/"
Write-Host "Pull $remote -> $localDir"

# scp -r надёжнее на Windows без WSL
& scp @sshArgs -r $remote "$localDir\"

if (Test-Path (Join-Path $localDir "SHA256SUMS.txt")) {
  Push-Location $localDir
  $sums = Get-Content SHA256SUMS.txt
  $fail = $false
  foreach ($line in $sums) {
    if ($line -match '^([a-f0-9]{64})\s+(.+)$') {
      $hash = $Matches[1]
      $file = $Matches[2]
      if (-not (Test-Path $file)) { continue }
      $actual = (Get-FileHash -Algorithm SHA256 $file).Hash.ToLower()
      if ($actual -ne $hash) {
        Write-Warning "SHA256 mismatch: $file"
        $fail = $true
      }
    }
  }
  Pop-Location
  if ($fail) { throw "Checksum verification failed" }
  Write-Host "SHA256 OK"
}

$latestLink = Join-Path $Dest "latest"
if (Test-Path $latestLink) { Remove-Item $latestLink -Force -Recurse -ErrorAction SilentlyContinue }
cmd /c "mklink /J `"$latestLink`" `"$localDir`"" 2>$null | Out-Null
if (-not (Test-Path $latestLink)) {
  Copy-Item -Path (Join-Path $localDir "*") -Destination (Join-Path $Dest "latest-copy") -Recurse -Force
  Write-Host "Note: junction latest not created; data in $localDir"
}

Write-Host "Cold copy ready: $localDir"
