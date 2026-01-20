#!/usr/bin/env python3
"""
List all tables in the database to find the correct table name
"""

import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Connecting to database...")
try:
    conn = pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'proxysql-office.taboolasyndication.com'),
        port=int(os.getenv('MYSQL_PORT', 6033)),
        user=os.getenv('MYSQL_USER', 'gaurav.k'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DB', 'trc'),
        charset='utf8mb4',
        client_flag=pymysql.constants.CLIENT.PLUGIN_AUTH
    )
    
    print("✅ Connected successfully!")
    print(f"\nTables in database '{os.getenv('MYSQL_DB', 'trc')}':")
    print("=" * 60)
    
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        if tables:
            for (table_name,) in tables:
                print(f"  - {table_name}")
                
            print(f"\nTotal tables: {len(tables)}")
            
            # Search for tables with 'project' or 'config' in name
            print("\n" + "=" * 60)
            print("Tables containing 'project' or 'config':")
            for (table_name,) in tables:
                if 'project' in table_name.lower() or 'config' in table_name.lower():
                    print(f"  ✓ {table_name}")
                    
            # Search for tables with 'alert' in name
            print("\n" + "=" * 60)
            print("Tables containing 'alert':")
            for (table_name,) in tables:
                if 'alert' in table_name.lower():
                    print(f"  ✓ {table_name}")
        else:
            print("  No tables found!")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
