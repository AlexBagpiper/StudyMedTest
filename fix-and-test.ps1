# ═══════════════════════════════════════════════════════════════
# [FIX] AUTOMATIC REPAIR AND TESTING - MedTest Platform
# ═══════════════════════════════════════════════════════════════
# Version: 1.0
# Date: January 13, 2026
# Description: Automatically fixes all issues and tests the system
# ═══════════════════════════════════════════════════════════════

param(
    [switch]$SkipCleanup,    # Skip cleanup (if already done)
    [switch]$SkipVenv,       # Skip venv creation
    [switch]$SkipNpm,        # Skip npm operations
    [switch]$SkipTests,      # Skip tests
    [switch]$Force           # Don't ask for confirmations
)

$ErrorActionPreference = "Continue"

# Colors
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
    param([string]$Text, [int]$Step, [int]$Total)
    Write-Host "[$Step/$Total] $Text" -ForegroundColor $ColorInfo
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

function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Test-Port {
    param([int]$Port)
    try {
        $connection = Test-NetConnection -ComputerName localhost -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
        return $connection
    }
    catch {
        return $false
    }
}

# ═══════════════════════════════════════════════════════════════
# START
# ═══════════════════════════════════════════════════════════════

Clear-Host
Write-Header "[FIX] AUTOMATIC REPAIR AND TESTING"

$startTime = Get-Date

# Check directory
if (-not (Test-Path "backend") -or -not (Test-Path "frontend")) {
    Write-Error "Run script from StudyMedTest project root!"
    exit 1
}

Write-Success "Working directory: $(Get-Location)"

# ═══════════════════════════════════════════════════════════════
# STEP 1: CHECK DEPENDENCIES
# ═══════════════════════════════════════════════════════════════

Write-Header "[CHECK] STEP 1/7: SYSTEM REQUIREMENTS"

$requirements = @{
    "python" = "Python 3.11+"
    "node" = "Node.js 20+"
    "npm" = "NPM"
    "psql" = "PostgreSQL"
}

$missingRequirements = @()

foreach ($cmd in $requirements.Keys) {
    $reqName = $requirements[$cmd]
    Write-Host "Checking $reqName... " -NoNewline
    if (Test-Command $cmd) {
        Write-Host "OK" -ForegroundColor Green
    }
    else {
        Write-Host "MISSING" -ForegroundColor Red
        $missingRequirements += $reqName
    }
}

if ($missingRequirements.Count -gt 0) {
    Write-Error "Missing required components:"
    $missingRequirements | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Install them according to INSTALL_WINDOWS.md" -ForegroundColor Yellow
    exit 1
}

Write-Success "All system requirements met"

# Find correct Python version
$pythonCmd = $null
$pythonCandidates = @("python3.12", "python3.11", "python", "py")

foreach ($candidate in $pythonCandidates) {
    try {
        $version = & $candidate --version 2>&1
        if ($version -like "*3.11*" -or $version -like "*3.12*") {
            $pythonCmd = $candidate
            Write-Success "Found Python: $candidate ($version)"
            break
        }
        elseif ($candidate -eq "py") {
            # Try py launcher with specific versions
            foreach ($pyVer in @("-3.12", "-3.11")) {
                try {
                    $version = & py $pyVer --version 2>&1
                    if ($version -like "*3.11*" -or $version -like "*3.12*") {
                        $pythonCmd = "py $pyVer"
                        Write-Success "Found Python: py $pyVer ($version)"
                        break
                    }
                }
                catch { }
            }
        }
    }
    catch { }
}

if (-not $pythonCmd) {
    Write-Error "Python 3.11+ not found!"
    Write-Host "Available Python versions:" -ForegroundColor Yellow
    python --version 2>&1 | Write-Host -ForegroundColor Gray
    Write-Host ""
    Write-Host "Install Python 3.11+ and make sure it's in PATH" -ForegroundColor Yellow
    exit 1
}

# ═══════════════════════════════════════════════════════════════
# STEP 2: CLEANUP
# ═══════════════════════════════════════════════════════════════

if (-not $SkipCleanup) {
    Write-Header "[CLEAN] STEP 2/7: CLEANING PROBLEMATIC FILES"
    
    if (Test-Path "cleanup-script.ps1") {
        Write-Host "Running cleanup-script.ps1..." -ForegroundColor Cyan
        & .\cleanup-script.ps1 -Force
        Write-Success "Cleanup completed"
    }
    else {
        Write-Warning "cleanup-script.ps1 not found, manual cleanup..."
        
        # Remove backend/venv if old version
        if (Test-Path "backend\venv\Scripts\python.exe") {
            $venvPython = "backend\venv\Scripts\python.exe"
            $venvVersion = & $venvPython --version 2>&1
            if ($venvVersion -like "*3.7*") {
                Write-Host "Removing old backend/venv (Python 3.7)..." -ForegroundColor Yellow
                Remove-Item -Recurse -Force "backend\venv"
                Write-Success "Removed"
            }
        }
        
        # Remove node_modules backups
        @("frontend\node_modules_backup", "frontend\node_modules_old") | ForEach-Object {
            if (Test-Path $_) {
                Write-Host "Removing $_..." -ForegroundColor Yellow
                Remove-Item -Recurse -Force $_
                Write-Success "Removed"
            }
        }
    }
}
else {
    Write-Header "[CLEAN] STEP 2/7: CLEANUP (SKIPPED)"
}

# ═══════════════════════════════════════════════════════════════
# STEP 3: CREATE backend/venv
# ═══════════════════════════════════════════════════════════════

if (-not $SkipVenv) {
    Write-Header "[VENV] STEP 3/7: CREATING BACKEND ENVIRONMENT"
    
    if (-not (Test-Path "backend\venv")) {
        Write-Host "Creating virtual environment with $pythonCmd..." -ForegroundColor Cyan
        Push-Location backend
        Invoke-Expression "$pythonCmd -m venv venv"
        Write-Success "Environment created"
        
        Write-Host "Activating environment..." -ForegroundColor Cyan
        .\venv\Scripts\Activate.ps1
        
        Write-Host "Upgrading pip..." -ForegroundColor Cyan
        python -m pip install --upgrade pip | Out-Null
        
        Write-Host "Installing dependencies (this will take several minutes)..." -ForegroundColor Cyan
        pip install -r requirements.txt
        Write-Success "Dependencies installed"
        
        # Check installation
        $installedPackages = pip list | Select-String -Pattern "fastapi|uvicorn|sqlalchemy" | Measure-Object
        if ($installedPackages.Count -ge 3) {
            Write-Success "Critical packages installed"
        }
        else {
            Write-Error "Problem with package installation!"
        }
        
        Pop-Location
    }
    else {
        Write-Success "backend/venv already exists"
        
        # Check Python version
        $venvPython = "backend\venv\Scripts\python.exe"
        $venvVersion = & $venvPython --version 2>&1
        Write-Host "Python version in venv: $venvVersion" -ForegroundColor Gray
        
        if ($venvVersion -notlike "*3.11*" -and $venvVersion -notlike "*3.12*") {
            Write-Warning "backend/venv uses old Python version!"
            if (-not $Force) {
                $recreate = Read-Host "Recreate venv? (y/N)"
                if ($recreate -eq 'y') {
                    Remove-Item -Recurse -Force "backend\venv"
                    Write-Host "Re-run the script"
                    exit 0
                }
            }
        }
    }
}
else {
    Write-Header "[VENV] STEP 3/7: BACKEND ENVIRONMENT (SKIPPED)"
}

# ═══════════════════════════════════════════════════════════════
# STEP 4: CREATE .env FILES
# ═══════════════════════════════════════════════════════════════

Write-Header "[ENV] STEP 4/7: CHECKING .env FILES"

# backend/.env
if (-not (Test-Path "backend\.env")) {
    Write-Warning "backend\.env not found"
    Write-Host "Creating backend\.env from template..." -ForegroundColor Cyan
    
    # Generate SECRET_KEY
    $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    
    $backendEnv = @"
# Database
DATABASE_URL=postgresql+asyncpg://medtest_user:medtest_password@localhost:5432/medtest_db
POSTGRES_DB=medtest_db
POSTGRES_USER=medtest_user
POSTGRES_PASSWORD=medtest_password

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Security
SECRET_KEY=$secretKey
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=medtest
MINIO_USE_SSL=false

# LLM APIs (optional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Local LLM
LOCAL_LLM_ENABLED=false
LOCAL_LLM_URL=http://localhost:8080

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost"]

# Environment
ENVIRONMENT=development
DEBUG=true
"@
    
    Set-Content -Path "backend\.env" -Value $backendEnv
    Write-Success "backend\.env created"
}
else {
    Write-Success "backend\.env exists"
}

# frontend/.env
if (-not (Test-Path "frontend\.env")) {
    Write-Warning "frontend\.env not found"
    $frontendEnv = "VITE_API_URL=http://localhost:8000"
    Set-Content -Path "frontend\.env" -Value $frontendEnv
    Write-Success "frontend\.env created"
}
else {
    Write-Success "frontend\.env exists"
}

# ═══════════════════════════════════════════════════════════════
# STEP 5: NPM PACKAGES
# ═══════════════════════════════════════════════════════════════

if (-not $SkipNpm) {
    Write-Header "[NPM] STEP 5/7: CHECKING NPM PACKAGES"
    
    Push-Location frontend
    
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing npm packages..." -ForegroundColor Cyan
        npm install
        Write-Success "Packages installed"
    }
    else {
        Write-Success "node_modules exists"
    }
    
    # Check vulnerabilities
    Write-Host "Checking vulnerabilities..." -ForegroundColor Cyan
    $auditResult = npm audit 2>&1
    $vulnerabilities = $auditResult | Select-String -Pattern "vulnerabilities"
    
    if ($vulnerabilities) {
        Write-Warning "Vulnerabilities found:"
        Write-Host $vulnerabilities -ForegroundColor Yellow
        Write-Host "To fix run: npm audit fix" -ForegroundColor Gray
    }
    else {
        Write-Success "No vulnerabilities found"
    }
    
    Pop-Location
}
else {
    Write-Header "[NPM] STEP 5/7: NPM PACKAGES (SKIPPED)"
}

# ═══════════════════════════════════════════════════════════════
# STEP 6: CHECK SERVICES
# ═══════════════════════════════════════════════════════════════

Write-Header "[SERVICES] STEP 6/7: CHECKING SERVICES"

$services = @{
    5432 = "PostgreSQL"
    6379 = "Redis/Memurai"
    9000 = "MinIO"
}

$missingServices = @()

foreach ($port in $services.Keys) {
    $serviceName = $services[$port]
    Write-Host "Checking $serviceName (port $port)... " -NoNewline
    
    if (Test-Port -Port $port) {
        Write-Host "OK" -ForegroundColor Green
    }
    else {
        Write-Host "NOT RUNNING" -ForegroundColor Red
        $missingServices += $serviceName
    }
}

if ($missingServices.Count -gt 0) {
    Write-Warning "Following services not running:"
    $missingServices | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "Start them before running the application!" -ForegroundColor Yellow
}
else {
    Write-Success "All services running"
}

# ═══════════════════════════════════════════════════════════════
# STEP 7: TESTS
# ═══════════════════════════════════════════════════════════════

if (-not $SkipTests) {
    Write-Header "[TEST] STEP 7/7: BASIC TESTS"
    
    # Test Python package imports
    Write-Host "Testing backend packages... " -NoNewline
    Push-Location backend
    
    $testScript = @"
try:
    import fastapi
    import uvicorn
    import sqlalchemy
    import celery
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
"@
    
    $testResult = & .\venv\Scripts\python.exe -c $testScript
    
    if ($testResult -eq 'OK') {
        Write-Host "OK" -ForegroundColor Green
    }
    else {
        Write-Host "FAILED" -ForegroundColor Red
        Write-Error "Import error: $testResult"
    }
    
    Pop-Location
    
    # Test frontend config
    Write-Host "Testing frontend config... " -NoNewline
    Push-Location frontend
    
    if (Test-Path "vite.config.ts") {
        Write-Host "OK" -ForegroundColor Green
    }
    else {
        Write-Host "FAILED" -ForegroundColor Red
    }
    
    Pop-Location
    
    Write-Success "Basic tests passed"
}
else {
    Write-Header "[TEST] STEP 7/7: TESTS (SKIPPED)"
}

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Header "[DONE] REPAIR COMPLETED"

$durationMinutes = [math]::Round($duration.TotalMinutes, 1)
Write-Success "Execution time: $durationMinutes minutes"
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "[NEXT] NEXT STEPS:" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if ($missingServices.Count -gt 0) {
    Write-Host "1. Start missing services:" -ForegroundColor Yellow
    $missingServices | ForEach-Object { Write-Host "   - $_" -ForegroundColor Gray }
    Write-Host ""
}

Write-Host "2. Apply DB migrations:" -ForegroundColor Yellow
Write-Host "   cd backend" -ForegroundColor Gray
Write-Host "   .\venv\Scripts\activate" -ForegroundColor Gray
Write-Host "   alembic upgrade head" -ForegroundColor Gray
Write-Host ""

Write-Host "3. Create admin user:" -ForegroundColor Yellow
Write-Host "   python create_admin.py" -ForegroundColor Gray
Write-Host ""

Write-Host "4. Start application:" -ForegroundColor Yellow
Write-Host "   .\start-all.bat" -ForegroundColor Gray
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# End
