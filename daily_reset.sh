#!/bin/bash
# Daily GeoEdge Reset Script Runner
# This script runs the reset inactive accounts process daily

# Set script directory
SCRIPT_DIR="/Users/gaurav.k/Desktop/geoedge-country-projects"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/daily_reset_$(date +%Y%m%d_%H%M%S).log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Change to script directory
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Add timestamp to log
echo "=== Daily Reset Job Started: $(date) ===" >> "$LOG_FILE"

# Run the reset script and capture output
python reset_inactive_accounts.py --all-projects >> "$LOG_FILE" 2>&1

# Check exit status
if [ $? -eq 0 ]; then
    echo "=== Daily Reset Job Completed Successfully: $(date) ===" >> "$LOG_FILE"
    exit 0
else
    echo "=== Daily Reset Job Failed: $(date) ===" >> "$LOG_FILE"
    exit 1
fi