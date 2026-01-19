# PowerShell script for daily GeoEdge account reset with auto-update from git
param(
    [switch]$Test,
    [string]$ConfigPath = "C:\nginx\html\geoedge-tools\resetgeoEdge"
)

# Configuration
$SCRIPT_DIR = $ConfigPath
# Update the above path to match your actual project location

# Create logs directory
$LogsDir = Join-Path $SCRIPT_DIR "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force
}

# Set log file with timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$LOG_FILE = Join-Path $LogsDir "daily_reset_$timestamp.log"

function Write-Log {
    param([string]$Message)
    $logEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'): $Message"
    Write-Output $logEntry
    Add-Content -Path $LOG_FILE -Value $logEntry
}

Write-Log "Starting daily GeoEdge reset"

try {
    # Change to script directory
    Set-Location $SCRIPT_DIR
    Write-Log "Changed to directory: $SCRIPT_DIR"

    # Update from git
    Write-Log "Updating from git repository..."
    $gitResult = & git pull origin main 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Git pull failed: $gitResult"
    }
    Write-Log "Git pull completed successfully"

    # Activate virtual environment
    Write-Log "Activating virtual environment..."
    $venvScript = $null
    if (Test-Path ".venv\Scripts\Activate.ps1") {
        $venvScript = ".venv\Scripts\Activate.ps1"
    } elseif (Test-Path "venv\Scripts\Activate.ps1") {
        $venvScript = "venv\Scripts\Activate.ps1"
    } else {
        throw "Virtual environment not found. Please run setup first."
    }
    
    & $venvScript
    Write-Log "Virtual environment activated"

    # Install/update requirements
    Write-Log "Updating requirements..."
    $pipResult = & pip install -r requirements.txt 2>&1
    Write-Log "Requirements updated"

    # Run the reset script
    Write-Log "Running reset inactive accounts script..."
    if ($Test) {
        Write-Log "TEST MODE: Would run reset_inactive_accounts.py"
        Write-Log "Test mode completed successfully"
    } else {
        $pythonResult = & python reset_inactive_accounts.py 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Python script failed: $pythonResult"
        }
        Write-Log "Reset script completed successfully"
    }

    Write-Log "Daily reset completed successfully"
    
} catch {
    $errorMsg = "ERROR: $($_.Exception.Message)"
    Write-Log $errorMsg
    Write-Error $errorMsg
    exit 1
}

Write-Log "Script execution completed. Check log file: $LOG_FILE"