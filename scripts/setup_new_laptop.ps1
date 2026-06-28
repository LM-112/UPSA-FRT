# =================================================================
# UPSA FRT — One-shot setup for a new Windows laptop.
# Usage:
#     powershell -ExecutionPolicy Bypass -File .\scripts\setup_new_laptop.ps1
#
# This script automates Steps 4 of MIGRATE_TO_DEMO_LAPTOP.md:
#   - verifies Python is on PATH
#   - creates a fresh venv
#   - installs requirements
#   - sets up the LOCALAPPDATA database location
#   - seeds the demo data
#   - generates the architecture diagrams
#   - runs the test suite
# =================================================================

$ErrorActionPreference = "Stop"

function Step($n, $msg) {
    Write-Host ""
    Write-Host "==[ Step $n ] $msg" -ForegroundColor Cyan
}

function Ok($msg)   { Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "  [XX]  $msg" -ForegroundColor Red; exit 1 }

# ----------------------------------------------------------------- 1. PATH check
Step 1 "Verifying Python is installed and on PATH"
$pyVer = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Fail "Python is not installed or not on PATH. Install Python 3.11 from https://www.python.org/downloads/windows/ and tick 'Add python.exe to PATH'."
}
Ok "Python detected: $pyVer"

# ----------------------------------------------------------------- 2. cwd check
Step 2 "Checking current working directory"
if (-not (Test-Path "run.py")) {
    Fail "run.py not found in current directory. cd into the project root first."
}
if (-not (Test-Path "requirements.txt")) {
    Fail "requirements.txt not found. This doesn't look like the project folder."
}
Ok "Project root confirmed: $(Get-Location)"

# ----------------------------------------------------------------- 3. fresh venv
Step 3 "Creating a fresh virtual environment in .\venv"
if (Test-Path "venv") {
    Warn "An existing venv was found. Removing it for a clean install..."
    Remove-Item -Recurse -Force venv
}
python -m venv venv
if ($LASTEXITCODE -ne 0) { Fail "Failed to create venv." }
Ok "venv created"

# ----------------------------------------------------------------- 4. activate
Step 4 "Activating the virtual environment"
. .\venv\Scripts\Activate.ps1
Ok "venv activated — prompt should now show (venv)"

# ----------------------------------------------------------------- 5. pip upgrade + install
Step 5 "Installing project dependencies (this takes 2-4 minutes)"
python -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -ne 0) { Fail "pip upgrade failed." }
Ok "pip upgraded"

pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { Fail "pip install failed. Check requirements.txt for issues." }
Ok "All requirements installed"

# ----------------------------------------------------------------- 6. database location
Step 6 "Configuring LOCALAPPDATA database location"
$dbDir = Join-Path $env:LOCALAPPDATA "UpsaFrt"
if (-not (Test-Path $dbDir)) {
    New-Item -ItemType Directory -Path $dbDir -Force | Out-Null
}
$dbPath = "sqlite:///" + ((Join-Path $dbDir "upsa_frt.db") -replace '\\','/')
$env:DATABASE_URL = $dbPath
Ok "Database will live at: $dbPath"

# Wipe any existing DB so seed creates fresh schema
$dbFile = Join-Path $dbDir "upsa_frt.db"
if (Test-Path $dbFile) {
    Remove-Item -Force $dbFile
    Ok "Previous database wiped (clean seed coming up)"
}

# ----------------------------------------------------------------- 7. seed
Step 7 "Seeding the database with UPSA demo data"
python run.py --seed
if ($LASTEXITCODE -ne 0) { Fail "Seed failed. Look above for the Python traceback." }
Ok "Database seeded with demo students, courses, sessions"

# ----------------------------------------------------------------- 8. diagrams
Step 8 "Generating architecture / ER / use-case diagrams"
python scripts\build_diagrams.py
if ($LASTEXITCODE -ne 0) { Warn "Diagram generation hiccup — non-fatal. Re-run python scripts\build_diagrams.py manually." }
else { Ok "Diagrams written to assets\diagrams\" }

# ----------------------------------------------------------------- 9. tests
Step 9 "Running the test suite"
python -m pytest tests\ -q --tb=short
if ($LASTEXITCODE -ne 0) {
    Fail "One or more tests failed. The system can still run, but investigate before the panel."
}
Ok "All tests passed"

# ----------------------------------------------------------------- 10. wrap-up
Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host "  UPSA FRT setup complete on this laptop." -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the application server:" -ForegroundColor White
Write-Host '  $env:DATABASE_URL = "' + $dbPath + '"' -ForegroundColor Yellow
Write-Host '  python run.py' -ForegroundColor Yellow
Write-Host ""
Write-Host "Then open in your browser: http://127.0.0.1:5000" -ForegroundColor White
Write-Host ""
Write-Host "Demo logins are printed in scripts\seed_demo.py output above." -ForegroundColor White
Write-Host ""
Write-Host "Next: run the live demo end-to-end with the Hikvision device" -ForegroundColor Cyan
Write-Host "      following Sections B and C of LIVE_DEMO_GUIDE.md." -ForegroundColor Cyan
Write-Host ""
