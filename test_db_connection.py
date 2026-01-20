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
print(f"MYSQL_HOST: {os.getenv('MYSQL_HOST')}")
print(f"MYSQL_PORT: {os.getenv('MYSQL_PORT')}")
print(f"MYSQL_USER: {os.getenv('MYSQL_USER')}")
print(f"MYSQL_DB: {os.getenv('MYSQL_DB')}")
print()

try:
    # Test connection with auth plugin
    conn = pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'proxysql-office.taboolasyndication.com'),
        port=int(os.getenv('MYSQL_PORT', 6033)),
        user=os.getenv('MYSQL_USER', 'gaurav.k'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DB', 'trc'),
        charset='utf8mb4',
        client_flag=pymysql.constants.CLIENT.PLUGIN_AUTH
    )
    
    print("✅ Database connection successful!")
    
    # Test a simple query
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(DISTINCT gep.project_id)
            FROM trc.geo_edge_projects AS gep
            JOIN trc.sp_campaigns sc ON gep.campaign_id = sc.id
            JOIN trc.sp_campaign_inventory_instructions sii ON gep.campaign_id = sii.campaign_id
            WHERE sii.instruction_status = 'ACTIVE'
              AND gep.creation_date >= '2025-10-01'
              AND gep.creation_date <= '2025-11-30'
              AND CONCAT(',', REPLACE(COALESCE(gep.locations, ''), ' ', ''), ',') REGEXP ',(IT|FR|DE|ES),'
        """)
        count = cursor.fetchone()[0]
        print(f"✅ Query successful! Found {count} configured projects")
    
    conn.close()
    print("✅ All tests passed!")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Verify .env file has DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME")
    print("2. Check VPN connection")
    print("3. Verify credentials are correct")
