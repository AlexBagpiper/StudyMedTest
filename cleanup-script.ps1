# ═══════════════════════════════════════════════════════════════
# [CLEANUP] АВТОМАТИЧЕСКАЯ ОЧИСТКА ПРОБЛЕМНЫХ ФАЙЛОВ - MedTest Platform
# ═══════════════════════════════════════════════════════════════
# Версия: 1.0
# Дата: 13 января 2026
# Описание: Удаляет конфликтные и проблемные файлы/директории
# ═══════════════════════════════════════════════════════════════

param(
    [switch]$DryRun,  # Показать что будет удалено без фактического удаления
    [switch]$Force    # Не спрашивать подтверждения
)

# Цвета для вывода
$ColorError = "Red"
$ColorWarning = "Yellow"
$ColorSuccess = "Green"
$ColorInfo = "Cyan"

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Text)
    Write-Host "> $Text" -ForegroundColor $ColorInfo
}

function Write-Success {
    param([string]$Text)
    Write-Host "[OK] $Text" -ForegroundColor $ColorSuccess
}

function Write-Warning {
    param([string]$Text)
    Write-Host "[!] $Text" -ForegroundColor $ColorWarning
}

function Write-Error {
    param([string]$Text)
    Write-Host "[X] $Text" -ForegroundColor $ColorError
}

function Get-DirectorySize {
    param([string]$Path)
    if (Test-Path $Path) {
        $size = (Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue | 
                 Measure-Object -Property Length -Sum).Sum
        return [math]::Round($size / 1MB, 2)
    }
    return 0
}

function Get-FileCount {
    param([string]$Path)
    if (Test-Path $Path) {
        return (Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue | 
                Measure-Object).Count
    }
    return 0
}

function Remove-DirectorySafely {
    param(
        [string]$Path,
        [string]$Description
    )
    
    if (-not (Test-Path $Path)) {
        Write-Warning "$Description not found: $Path"
        return
    }
    
    $sizeMB = Get-DirectorySize -Path $Path
    $fileCount = Get-FileCount -Path $Path
    
    Write-Step "$Description"
    Write-Host "   Path: $Path" -ForegroundColor Gray
    Write-Host "   Size: $sizeMB MB" -ForegroundColor Gray
    Write-Host "   Files: $fileCount" -ForegroundColor Gray
    
    if ($DryRun) {
        Write-Warning "[DRY RUN] Will be deleted: $Path"
        return
    }
    
    if (-not $Force) {
        $confirm = Read-Host "   Delete? (y/N)"
        if ($confirm -ne 'y' -and $confirm -ne 'Y') {
            Write-Warning "Skipped"
            return
        }
    }
    
    try {
        Write-Host "   Deleting..." -ForegroundColor Yellow -NoNewline
        Remove-Item -Path $Path -Recurse -Force -ErrorAction Stop
        Write-Host " Done!" -ForegroundColor Green
        Write-Success "Deleted $sizeMB MB ($fileCount files)"
        return $sizeMB
    }
    catch {
        Write-Error "Error deleting: $_"
        return 0
    }
}

# ═══════════════════════════════════════════════════════════════
# SCRIPT START
# ═══════════════════════════════════════════════════════════════

Clear-Host
Write-Header "[CLEANUP] CLEANING PROBLEMATIC FILES"

if ($DryRun) {
    Write-Warning "TEST MODE (Dry Run) - nothing will be deleted"
    Write-Host ""
}

# Check we are in the right directory
if (-not (Test-Path "backend") -or -not (Test-Path "frontend")) {
    Write-Error "Error: Run script from StudyMedTest project root!"
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    exit 1
}

Write-Success "Correct directory: $(Get-Location)"
Write-Host ""

$totalSpaceFreed = 0
$itemsToRemove = @()

# ═══════════════════════════════════════════════════════════════
# SCANNING
# ═══════════════════════════════════════════════════════════════

Write-Header "[SCAN] ANALYZING PROBLEMATIC FILES"

# 1. backend/venv (Python 3.7.9)
if (Test-Path "backend\venv") {
    $venvPython = "backend\venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        try {
            $pythonVersion = & $venvPython --version 2>&1
            Write-Step "backend\venv found: $pythonVersion"
            
            if ($pythonVersion -like "*3.7*") {
                Write-Error "CRITICAL: Uses Python 3.7 (EOL, incompatible with project)"
                $itemsToRemove += @{
                    Path = "backend\venv"
                    Description = "[CRITICAL] backend\venv (Python 3.7.9 - CRITICAL)"
                    Priority = 1
                }
            }
            elseif ($pythonVersion -like "*3.11*") {
                Write-Success "backend\venv uses Python 3.11 - OK"
            }
        }
        catch {
            Write-Warning "Could not determine Python version in backend\venv"
        }
    }
}

# 2. node_modules_backup
if (Test-Path "frontend\node_modules_backup") {
    $size = Get-DirectorySize -Path "frontend\node_modules_backup"
    $count = Get-FileCount -Path "frontend\node_modules_backup"
    $sizeStr = $size.ToString()
    $countStr = $count.ToString()
    Write-Step "node_modules_backup found: $sizeStr MB, $countStr files"
    Write-Warning "Takes up a lot of space and is not used"
    $desc = "[DELETE] node_modules_backup (" + $sizeStr + " MB, " + $countStr + " files)"
    $itemsToRemove += @{
        Path = "frontend\node_modules_backup"
        Description = $desc
        Priority = 2
    }
}

# 3. node_modules_old
if (Test-Path "frontend\node_modules_old") {
    $size = Get-DirectorySize -Path "frontend\node_modules_old"
    $count = Get-FileCount -Path "frontend\node_modules_old"
    $sizeStr = $size.ToString()
    $countStr = $count.ToString()
    Write-Step "node_modules_old found: $sizeStr MB, $countStr files"
    Write-Warning "Old backup, not used"
    $desc = "[DELETE] node_modules_old (" + $sizeStr + " MB, " + $countStr + " files)"
    $itemsToRemove += @{
        Path = "frontend\node_modules_old"
        Description = $desc
        Priority = 3
    }
}

# 4. __pycache__ directories
$pycacheCount = (Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Measure-Object).Count
if ($pycacheCount -gt 0) {
    Write-Step "Found $pycacheCount __pycache__ directories"
    Write-Host "   (Will be cleaned automatically)" -ForegroundColor Gray
}

Write-Host ""

# ═══════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════

if ($itemsToRemove.Count -eq 0) {
    Write-Header "[OK] NO PROBLEMS FOUND"
    Write-Success "All files and directories are OK!"
    exit 0
}

Write-Header "[PLAN] DELETION PLAN"

$itemsToRemove = $itemsToRemove | Sort-Object -Property Priority

foreach ($item in $itemsToRemove) {
    Write-Host "  $($item.Description)" -ForegroundColor Yellow
    Write-Host "    Path: $($item.Path)" -ForegroundColor Gray
}

Write-Host ""
$totalSize = ($itemsToRemove | ForEach-Object { Get-DirectorySize -Path $_.Path } | Measure-Object -Sum).Sum
$totalSizeRounded = [math]::Round($totalSize, 2)
Write-Host "Will free up: ~$totalSizeRounded MB" -ForegroundColor Cyan
Write-Host ""

if (-not $Force -and -not $DryRun) {
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "[!] WARNING! This action is irreversible!" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host ""
    $confirmAll = Read-Host "Continue deleting all files? (y/N)"
    if ($confirmAll -ne 'y' -and $confirmAll -ne 'Y') {
        Write-Warning "Cancelled by user"
        exit 0
    }
    Write-Host ""
}

# ═══════════════════════════════════════════════════════════════
# DELETION
# ═══════════════════════════════════════════════════════════════

Write-Header "[DELETE] DELETING FILES"

foreach ($item in $itemsToRemove) {
    $freed = Remove-DirectorySafely -Path $item.Path -Description $item.Description
    $totalSpaceFreed += $freed
    Write-Host ""
}

# Delete __pycache__
if (-not $DryRun) {
    Write-Step "Cleaning __pycache__ directories..."
    try {
        Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | 
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Write-Success "All __pycache__ directories cleaned"
    }
    catch {
        Write-Warning "Could not clean some __pycache__ directories"
    }
}

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════

Write-Host ""
Write-Header "[DONE] CLEANUP COMPLETED"

if ($DryRun) {
    Write-Warning "This was a test run. For actual deletion run:"
    Write-Host ".\cleanup-script.ps1 -Force" -ForegroundColor Cyan
}
else {
    $totalFreedRounded = [math]::Round($totalSpaceFreed, 2)
    Write-Success "Disk space freed: ~$totalFreedRounded MB"
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "[NEXT] NEXT STEPS:" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    # Check what was deleted
    $needsNewVenv = $itemsToRemove | Where-Object { $_.Path -eq "backend\venv" }
    
    if ($needsNewVenv) {
        Write-Host "1. Create new backend/venv with Python 3.11:" -ForegroundColor Yellow
        Write-Host "   cd backend" -ForegroundColor Gray
        Write-Host "   python -m venv venv" -ForegroundColor Gray
        Write-Host "   .\venv\Scripts\activate" -ForegroundColor Gray
        Write-Host "   pip install -r requirements.txt" -ForegroundColor Gray
        Write-Host ""
    }
    
    Write-Host "2. Create .env files (if missing):" -ForegroundColor Yellow
    Write-Host "   Use templates from DIAGNOSTIC_REPORT.md" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "3. Apply DB migrations:" -ForegroundColor Yellow
    Write-Host "   cd backend" -ForegroundColor Gray
    Write-Host "   .\venv\Scripts\activate" -ForegroundColor Gray
    Write-Host "   alembic upgrade head" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "4. Create admin user:" -ForegroundColor Yellow
    Write-Host "   python create_admin.py" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "5. Run application:" -ForegroundColor Yellow
    Write-Host "   .\start-all.bat" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Full report see DIAGNOSTIC_REPORT.md" -ForegroundColor Gray
Write-Host ""

# End of script
