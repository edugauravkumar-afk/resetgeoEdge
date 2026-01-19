#!/usr/bin/env python3
"""
Project Account Lookup - Get account ID and country for a project ID
Filters for LATAM and Greater China accounts only
"""

import os
import sys
import pymysql
from pymysql import MySQLError
from dotenv import load_dotenv

load_dotenv()

# Regional country codes
LATAM_COUNTRIES = {"MX", "AR", "BR", "CL", "CO", "PE"}
GREATER_CHINA_COUNTRIES = {"CN", "HK", "TW", "MO"}
TARGET_REGIONS = LATAM_COUNTRIES | GREATER_CHINA_COUNTRIES

# Country display names
COUNTRY_DISPLAY = {
    # LATAM
    "MX": "🇲🇽 Mexico",
    "AR": "🇦🇷 Argentina", 
    "BR": "🇧🇷 Brazil",
    "CL": "🇨🇱 Chile",
    "CO": "🇨🇴 Colombia",
    "PE": "🇵🇪 Peru",
    # Greater China
    "CN": "🇨🇳 China",
    "HK": "🇭🇰 Hong Kong",
    "TW": "🇹🇼 Taiwan",
    "MO": "🇲🇴 Macau",
}

def _env_or_fail(key: str) -> str:
    """Get environment variable or fail"""
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value

def get_database_connection():
    """Create MySQL database connection"""
    host = _env_or_fail("MYSQL_HOST")
    port = int(os.getenv("MYSQL_PORT", "6033"))
    user = _env_or_fail("MYSQL_USER")
    password = _env_or_fail("MYSQL_PASSWORD")
    database = _env_or_fail("MYSQL_DB")
    
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor,
    )

def lookup_project_account_info(project_id: str):
    """
    Lookup account ID and country for a given project ID
    Returns only LATAM and Greater China accounts
    """
    
    print(f"🔍 Looking up project: {project_id}")
    print("=" * 50)
    
    try:
        connection = get_database_connection()
        
        with connection.cursor() as cursor:
            # Step 1: Get campaigns for this project
            print("Step 1: Finding campaigns for project...")
            sql = """
                SELECT DISTINCT campaign_id, locations
                FROM trc.geo_edge_projects
                WHERE project_id = %s OR id = %s
            """
            cursor.execute(sql, (project_id, project_id))
            campaigns = cursor.fetchall()
            
            if not campaigns:
                print(f"❌ No campaigns found for project ID: {project_id}")
                return
            
            print(f"✅ Found {len(campaigns)} campaign(s)")
            
            results = []
            
            for campaign in campaigns:
                campaign_id = campaign["campaign_id"]
                locations = campaign.get("locations", "")
                
                print(f"\n📊 Processing campaign: {campaign_id}")
                print(f"   Target locations: {locations}")
                
                # Step 2: Get advertiser ID from landing pages
                sql = """
                    SELECT advertiser_id
                    FROM trc.geo_edge_landing_pages
                    WHERE campaign_id = %s
                    LIMIT 1
                """
                cursor.execute(sql, (campaign_id,))
                lp_result = cursor.fetchone()
                
                if not lp_result:
                    print(f"   ❌ No landing page found for campaign {campaign_id}")
                    continue
                
                advertiser_id = lp_result["advertiser_id"]
                print(f"   ✅ Advertiser ID: {advertiser_id}")
                
                # Step 3: Get account ID from advertiser accounts
                sql = """
                    SELECT account_id, name AS publisher_name
                    FROM trc.advertiser_accounts
                    WHERE id = %s
                    LIMIT 1
                """
                cursor.execute(sql, (advertiser_id,))
                account_result = cursor.fetchone()
                
                if not account_result:
                    print(f"   ❌ No account found for advertiser {advertiser_id}")
                    continue
                
                account_id = account_result["account_id"]
                publisher_name = account_result["publisher_name"]
                print(f"   ✅ Account ID: {account_id}")
                print(f"   ✅ Publisher: {publisher_name}")
                
                # Step 4: Get country from publishers
                sql = """
                    SELECT country
                    FROM trc.publishers
                    WHERE id = %s
                    LIMIT 1
                """
                cursor.execute(sql, (account_id,))
                country_result = cursor.fetchone()
                
                if not country_result:
                    print(f"   ❌ No country found for account {account_id}")
                    continue
                
                country = country_result["country"]
                country_display = COUNTRY_DISPLAY.get(country, f"🌍 {country}")
                
                # Step 5: Check if it's in target regions (LATAM or Greater China)
                if country in TARGET_REGIONS:
                    region_type = "LATAM" if country in LATAM_COUNTRIES else "Greater China"
                    print(f"   ✅ Country: {country_display} ({region_type})")
                    
                    results.append({
                        "project_id": project_id,
                        "campaign_id": campaign_id,
                        "account_id": account_id,
                        "publisher_name": publisher_name,
                        "country": country,
                        "country_display": country_display,
                        "region_type": region_type,
                        "locations": locations
                    })
                else:
                    print(f"   ⚠️ Country: {country_display} (Not in target regions)")
        
        connection.close()
        
        # Display results
        print("\n" + "=" * 60)
        print("📋 FINAL RESULTS - LATAM & GREATER CHINA ACCOUNTS")
        print("=" * 60)
        
        if not results:
            print("❌ No accounts found in LATAM or Greater China regions")
            return
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. 🎯 Match Found:")
            print(f"   Project ID: {result['project_id']}")
            print(f"   Campaign ID: {result['campaign_id']}")
            print(f"   Account ID: {result['account_id']}")
            print(f"   Publisher: {result['publisher_name']}")
            print(f"   Country: {result['country_display']}")
            print(f"   Region: ⭐ {result['region_type']}")
            print(f"   Target Locations: {result['locations']}")
        
        print(f"\n✅ Total matches: {len(results)}")
        
        return results
        
    except MySQLError as e:
        print(f"❌ Database error: {str(e)}")
        return None
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python lookup_project_account.py <project_id>")
        print("Example: python lookup_project_account.py 12345")
        sys.exit(1)
    
    project_id = sys.argv[1].strip()
    
    if not project_id:
        print("❌ Please provide a valid project ID")
        sys.exit(1)
    
    print("🌍 PROJECT ACCOUNT LOOKUP - LATAM & GREATER CHINA")
    print("=" * 60)
    
    # Check environment variables
    required_vars = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DB"]
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("Please ensure your .env file is configured with database credentials")
        sys.exit(1)
    
    # Perform lookup
    results = lookup_project_account_info(project_id)
    
    if results:
        print(f"\n🎉 Success! Found {len(results)} account(s) in target regions")
    else:
        print("\n⚠️ No results found or error occurred")

if __name__ == "__main__":
    main()