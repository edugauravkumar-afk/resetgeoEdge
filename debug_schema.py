#!/usr/bin/env python3
"""
Quick database schema debug tool
"""
import os
import sys
import pymysql

def check_schema():
    try:
        # Database connection
        db = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'TRC'),
            charset='utf8mb4'
        )
        
        cursor = db.cursor()
        
        print("🔍 CHECKING KEY TABLES SCHEMA")
        print("=" * 50)
        
        # Check publishers table
        print("\n📊 Publishers table columns:")
        cursor.execute("DESCRIBE publishers")
        publishers_cols = cursor.fetchall()
        for col in publishers_cols:
            print(f"   • {col[0]:<25} {col[1]:<20}")
        
        # Check geo_edge_projects table  
        print("\n📊 Geo Edge Projects table columns:")
        cursor.execute("DESCRIBE geo_edge_projects")
        projects_cols = cursor.fetchall()
        for col in projects_cols:
            print(f"   • {col[0]:<25} {col[1]:<20}")
        
        # Check sp_campaigns table
        print("\n📊 SP Campaigns table columns:")
        cursor.execute("DESCRIBE sp_campaigns")
        campaigns_cols = cursor.fetchall()
        for col in campaigns_cols:
            print(f"   • {col[0]:<25} {col[1]:<20}")
            
        # Check if there's a syndicators table
        print("\n📊 Checking for syndicators table...")
        cursor.execute("SHOW TABLES LIKE '%syndic%'")
        syndicator_tables = cursor.fetchall()
        for table in syndicator_tables:
            print(f"   • Found table: {table[0]}")
        
        cursor.close()
        db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_schema()