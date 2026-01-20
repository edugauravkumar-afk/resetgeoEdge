#!/usr/bin/env python3
"""
GeoEdge Monitor - Simple startup script
Run this once and it will automatically execute daily monitoring
"""

import sys
import os
from daily_monitor_service import GeoEdgeDailyService

def main():
    print("🚀 Starting GeoEdge Daily Monitor Service")
    print("=" * 50)
    print("✅ Automatic daily monitoring at 9:00 AM")
    print("📧 Email reports sent automatically")  
    print("🔄 Runs continuously in background")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 50)
    
    # Start the service
    service = GeoEdgeDailyService()
    service.start_service()

if __name__ == "__main__":
    main()