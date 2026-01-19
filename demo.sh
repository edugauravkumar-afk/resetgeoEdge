#!/bin/bash
# Demo script showing different ways to use the GeoEdge Projects tools

echo "🌍 GeoEdge Projects Tools Demo"
echo "================================="
echo ""

# Set environment variables
set -a
source .env
set +a

echo "1. 📊 Starting Streamlit Dashboard..."
echo "   Opening browser at http://localhost:8501"
echo "   (Dashboard will run in background)"
echo ""

# Note: Streamlit is already running from previous command

echo "2. 🔍 Command-line Query Examples:"
echo ""

echo "   Example 1: Basic query (MySQL, last 7 days, IT/FR/DE/ES)"
echo "   Command: python query_projects.py --limit 3"
echo ""
/Users/gaurav.k/Desktop/geoedge-country-projects/.venv/bin/python query_projects.py --limit 3
echo ""

echo "   Example 2: JSON output"
echo "   Command: python query_projects.py --json --limit 2"
echo ""
/Users/gaurav.k/Desktop/geoedge-country-projects/.venv/bin/python query_projects.py --json --limit 2
echo ""

echo "   Example 3: Different countries and time range"
echo "   Command: python query_projects.py --days 14 --countries FR,DE --limit 2"
echo ""
/Users/gaurav.k/Desktop/geoedge-country-projects/.venv/bin/python query_projects.py --days 14 --countries FR,DE --limit 2
echo ""

echo "🎯 Available Features:"
echo "   ✅ Interactive web dashboard (running at http://localhost:8501)"
echo "   ✅ Command-line interface with Excel/JSON export"
echo "   ✅ Real-time filtering and data exploration"
echo "   ✅ GeoEdge API integration for detailed project info"
echo "   ✅ Support for both MySQL and Vertica databases"
echo ""

echo "📖 For more options, run: python query_projects.py --help"