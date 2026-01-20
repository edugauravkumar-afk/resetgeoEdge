#!/usr/bin/env python3
"""
Quick test to verify database connection works on Windows
"""

import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Testing database connection...")
print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_PORT: {os.getenv('DB_PORT')}")
print(f"DB_USER: {os.getenv('DB_USER')}")
print(f"DB_NAME: {os.getenv('DB_NAME')}")
print()

try:
    # Test connection with auth plugin
    conn = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 6033)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        charset='utf8mb4',
        client_flag=pymysql.constants.CLIENT.PLUGIN_AUTH
    )
    
    print("✅ Database connection successful!")
    
    # Test a simple query
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM project_config WHERE auto_scan = 1 AND times_per_day = 72")
        count = cursor.fetchone()[0]
        print(f"✅ Query successful! Found {count} projects with Auto Mode (1,72)")
    
    conn.close()
    print("✅ All tests passed!")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Verify .env file has DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME")
    print("2. Check VPN connection")
    print("3. Verify credentials are correct")
