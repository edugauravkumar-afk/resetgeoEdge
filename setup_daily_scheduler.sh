#!/bin/bash

# GeoEdge Daily Monitor Scheduler Setup
# This script sets up a daily cron job to run the inactive account monitor

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/daily_inactive_monitor.py"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Virtual environment not found at $VENV_PYTHON"
    echo "Please run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Daily monitor script not found at $PYTHON_SCRIPT"
    exit 1
fi

# Create wrapper script for cron
WRAPPER_SCRIPT="$SCRIPT_DIR/run_daily_monitor.sh"

cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
# Daily Monitor Wrapper Script
# Generated on $(date)

cd "$SCRIPT_DIR"
source "$SCRIPT_DIR/.venv/bin/activate"
"$VENV_PYTHON" "$PYTHON_SCRIPT" >> "$SCRIPT_DIR/logs/daily_monitor_\$(date +%Y%m%d).log" 2>&1
EOF

chmod +x "$WRAPPER_SCRIPT"

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

echo "✅ Created wrapper script: $WRAPPER_SCRIPT"

# Create cron job entry
CRON_ENTRY="0 9 * * * $WRAPPER_SCRIPT"

echo ""
echo "📅 To schedule the daily monitor, add this cron job:"
echo "Run: crontab -e"
echo "Add this line:"
echo "$CRON_ENTRY"
echo ""
echo "This will run the monitor daily at 9:00 AM"
echo ""
echo "Alternative times:"
echo "# Every day at 6:00 AM: 0 6 * * * $WRAPPER_SCRIPT"
echo "# Every day at 8:30 AM: 30 8 * * * $WRAPPER_SCRIPT" 
echo "# Every day at 10:00 PM: 0 22 * * * $WRAPPER_SCRIPT"
echo ""

# Test run option
read -p "🧪 Would you like to test run the daily monitor now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Running test..."
    "$WRAPPER_SCRIPT"
    echo "✅ Test completed. Check the log files in $SCRIPT_DIR/logs/"
else
    echo "ℹ️  You can test manually later with: $WRAPPER_SCRIPT"
fi

echo ""
echo "📊 Monitor Setup Complete!"
echo "Log files will be stored in: $SCRIPT_DIR/logs/"
echo "State file will be stored as: $SCRIPT_DIR/daily_monitor_state.json"