# PowerShell Daily GeoEdge Reset Script
# This script runs the reset inactive accounts process daily

param(
    [string]$ScriptDir = "C:\path\to\geoedge-country-projects",
    [switch]$Test
)

# Configuration
$LogDir = Join-Path $ScriptDir "logs"
$LogFile = Join-Path $LogDir "daily_reset_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Ensure log directory exists
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force
}

# Function to write log with timestamp
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "$timestamp - $Message"
    Write-Host $logMessage
    Add-Content -Path $LogFile -Value $logMessage
}

try {
    Write-Log "Starting daily reset job..."
    
    # Change to script directory
    Set-Location $ScriptDir
    
    # Activate virtual environment if it exists
    $venvActivate = Join-Path $ScriptDir ".venv\Scripts\Activate.ps1"
    if (Test-Path $venvActivate) {
        Write-Log "Activating virtual environment..."
        & $venvActivate
    }
    
    # Run the reset script
    Write-Log "Executing reset script..."
    $output = python reset_inactive_accounts.py --all-projects 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Daily reset job completed successfully"
        Write-Log "Script output: $output"
    } else {
        Write-Log "Daily reset job failed with exit code $LASTEXITCODE"
        Write-Log "Error output: $output"
        exit 1
    }
    
} catch {
    Write-Log "Unexpected error: $($_.Exception.Message)"
    exit 1
}