#!/usr/bin/env python3
"""
Test script to explore GeoEdge location targeting options
"""

import json
from geoedge_projects.client import GeoEdgeClient

def explore_geoedge_locations():
    """Check what location targeting options are available in GeoEdge API"""
    try:
        client = GeoEdgeClient()
        
        print("🌍 Fetching available GeoEdge locations...")
        print("=" * 60)
        
        # Get all available locations
        locations = client.list_locations()
        
        if not locations:
            print("❌ No locations found or API error")
            return
        
        print(f"✅ Found {len(locations)} available locations:")
        print("-" * 60)
        
        # Sort by ID for better organization
        sorted_locations = sorted(locations.items(), key=lambda x: str(x[0]))
        
        # Categorize locations
        countries = []
        cities = []
        regions = []
        others = []
        
        for loc_id, description in sorted_locations:
            print(f"ID: {loc_id:15} | Description: {description}")
            
            # Categorize based on description patterns
            desc_lower = description.lower()
            if any(city in desc_lower for city in ['new york', 'los angeles', 'chicago', 'miami', 'boston', 'seattle', 'atlanta', 'dallas', 'denver', 'portland']):
                cities.append((loc_id, description))
            elif len(description) == 2 and description.isupper():  # Country codes like US, UK, DE
                countries.append((loc_id, description))
            elif 'region' in desc_lower or 'continent' in desc_lower:
                regions.append((loc_id, description))
            else:
                others.append((loc_id, description))
        
        print("\n" + "=" * 60)
        print("📊 LOCATION ANALYSIS:")
        print("=" * 60)
        
        if cities:
            print(f"\n🏙️  CITIES ({len(cities)} found):")
            for loc_id, desc in cities:
                print(f"   - {loc_id}: {desc}")
        
        if countries:
            print(f"\n🌎 COUNTRIES ({len(countries)} found):")
            for loc_id, desc in countries[:10]:  # Show first 10
                print(f"   - {loc_id}: {desc}")
            if len(countries) > 10:
                print(f"   ... and {len(countries) - 10} more")
        
        if regions:
            print(f"\n🌍 REGIONS ({len(regions)} found):")
            for loc_id, desc in regions:
                print(f"   - {loc_id}: {desc}")
        
        if others:
            print(f"\n🔍 OTHER LOCATIONS ({len(others)} found):")
            for loc_id, desc in others[:10]:  # Show first 10
                print(f"   - {loc_id}: {desc}")
            if len(others) > 10:
                print(f"   ... and {len(others) - 10} more")
        
        print("\n" + "=" * 60)
        print("🎯 TARGETING RECOMMENDATIONS:")
        print("=" * 60)
        
        # Look for New York specifically
        ny_locations = [(loc_id, desc) for loc_id, desc in sorted_locations if 'new york' in desc.lower() or 'ny' in desc.lower()]
        if ny_locations:
            print("✅ NEW YORK TARGETING AVAILABLE:")
            for loc_id, desc in ny_locations:
                print(f"   🗽 Use location_id: '{loc_id}' for '{desc}'")
        else:
            print("❌ No specific New York city targeting found")
            print("💡 You may need to use 'US' for United States targeting")
        
        # Look for other major US cities
        us_cities = [(loc_id, desc) for loc_id, desc in sorted_locations 
                    if any(city in desc.lower() for city in ['los angeles', 'chicago', 'miami', 'boston', 'seattle'])]
        if us_cities:
            print("\n✅ OTHER US CITIES AVAILABLE:")
            for loc_id, desc in us_cities[:5]:
                print(f"   🏙️  Use location_id: '{loc_id}' for '{desc}'")
        
        # Save complete list to file for reference
        with open('/Users/gaurav.k/Desktop/geoedge-country-projects/geoedge_locations.json', 'w') as f:
            json.dump(locations, f, indent=2, sort_keys=True)
        
        print(f"\n💾 Complete location list saved to 'geoedge_locations.json'")
        print(f"\n📋 USAGE IN DASHBOARD:")
        print("   - Update the alerts dashboard to use these location_ids")
        print("   - Replace country dropdowns with city-level targeting")
        print("   - Allow multiple location selection for broader campaigns")
        
    except Exception as e:
        print(f"❌ Error exploring locations: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    explore_geoedge_locations()