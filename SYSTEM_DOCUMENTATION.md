# 🎯 GeoEdge Project Manager - System Documentation

## 📋 Overview
This system provides a comprehensive solution for managing GeoEdge project configurations with a user-friendly web interface.

## 🚀 Key Features

### 1. **Configurable Lookback Period**
- **What it does**: Allows manager to specify how many days back to fetch projects
- **Default**: 7 days
- **Range**: 1-365 days
- **Usage**: Change the number in sidebar → Click "Load Projects"

### 2. **Location Filtering**
- **What it does**: Filter projects by target countries
- **Options**: IT (Italy), FR (France), DE (Germany), ES (Spain)
- **Usage**: Select/deselect countries in sidebar

### 3. **Visual Status Indicators**
- **🟢 Green rows**: Projects already correctly configured
- **🟡 Yellow rows**: Projects that need updating
- **🔴 Red rows**: Projects with API access issues

### 4. **One-Click Bulk Updates**
- **What it does**: Updates all projects that need configuration changes
- **Process**: Automatically updates auto_scan and times_per_day values
- **Progress**: Shows real-time progress during updates

### 5. **Real-Time Statistics**
- **Total Projects**: Number of projects found
- **Correctly Configured**: Projects already with target configuration
- **Needs Update**: Projects requiring configuration changes
- **API Errors**: Projects that couldn't be accessed

## 🔧 How to Change Configuration

### **Days to Look Back**
```python
# In the sidebar, change this value:
days_back = st.sidebar.number_input(
    "📅 Days to Look Back",
    min_value=1,
    max_value=365,
    value=7,  # ← Change this default value
)
```

### **Target Configuration Values**
```python
# In the sidebar, change these values:
target_auto_scan = st.sidebar.number_input("Auto Scan Value", value=1)  # ← Default auto_scan
target_times_per_day = st.sidebar.number_input("Times Per Day Value", value=72)  # ← Default times_per_day
```

### **Target Countries**
```python
# Change the available locations:
available_locations = ['IT', 'FR', 'DE', 'ES']  # ← Add/remove countries
selected_locations = st.sidebar.multiselect(
    "🌍 Target Locations",
    available_locations,
    default=available_locations,  # ← Change default selection
)
```

## 📊 System Workflow

### **Step 1: Data Fetching**
```sql
-- System runs this query:
SELECT DISTINCT
    p.project_id,
    p.campaign_id,
    p.locations,
    p.creation_date,
    sii.instruction_status
FROM trc.geo_edge_projects AS p
JOIN trc.sp_campaign_inventory_instructions sii ON p.campaign_id = sii.campaign_id
WHERE sii.instruction_status = 'ACTIVE' 
  AND p.creation_date >= DATE_SUB(NOW(), INTERVAL {days_back} DAY)
  AND CONCAT(',', REPLACE(COALESCE(p.locations, ''), ' ', ''), ',') REGEXP ',(IT|FR|DE|ES),'
ORDER BY p.creation_date DESC
```

### **Step 2: API Status Check**
```python
# For each project, system calls:
GET https://api.geoedge.com/rest/analytics/v3/projects/{project_id}

# Extracts current values:
current_auto_scan = project.get('auto_scan', 0)
current_times_per_day = project.get('times_per_day', 0)
```

### **Step 3: Configuration Analysis**
```python
# System determines if project needs update:
is_correct = (current_auto_scan == target_auto_scan and 
              current_times_per_day == target_times_per_day)
needs_update = not is_correct and api_accessible
```

### **Step 4: Bulk Update (if requested)**
```python
# For projects needing updates:
PUT https://api.geoedge.com/rest/analytics/v3/projects/{project_id}
{
    "auto_scan": target_auto_scan,
    "times_per_day": target_times_per_day
}
```

## 🎨 User Interface Guide

### **Sidebar Controls**
- **Days to Look Back**: Slider/input for lookback period
- **Target Locations**: Multi-select for countries
- **Target Configuration**: Input fields for auto_scan and times_per_day values
- **Load Projects**: Button to refresh data

### **Main Dashboard**
- **Summary Cards**: Statistics overview
- **Update Button**: Appears when projects need updates
- **Projects Table**: Color-coded table with all project details
- **Download Button**: Export data as CSV

### **Color Coding System**
- **Green Background**: `✅ Correctly configured` (auto_scan=1, times_per_day=72)
- **Yellow Background**: `🔧 Needs update` (different values)
- **Red Background**: `⚠️ API errors` (couldn't access project)

## 🔧 Running the System

### **Start the Enhanced Manager**
```bash
cd /Users/gaurav.k/Desktop/geoedge-country-projects
.venv/bin/python -m streamlit run enhanced_manager.py
```

### **Access the Dashboard**
- Open browser to: `http://localhost:8501`
- Use sidebar controls to configure parameters
- Click "Load Projects" to fetch data
- Review the color-coded table
- Click "Update X Projects" to apply changes

## 📈 Summary Display Logic

The system shows a summary like:
```
📊 Configuration Summary
┌─────────────────┬──────────────────────┬──────────────┬─────────────┐
│ Total Projects  │ Correctly Configured │ Needs Update │ API Errors  │
│      150        │      120 (80.0%)     │      25      │      5      │
└─────────────────┴──────────────────────┴──────────────┴─────────────┘

Out of 150 projects, 120 are already correctly configured (80% success rate)
```

## 🔄 Auto-Refresh and Caching

- **Data Caching**: Results cached for 5 minutes to improve performance
- **Cache Clearing**: "Load Projects" button clears cache for fresh data
- **Auto-Refresh**: After bulk updates, page automatically refreshes to show new status

## 💾 Export and Reporting

- **CSV Export**: Download complete project report with all details
- **Timestamp**: Files include timestamp in filename
- **Data Included**: All project details, current configuration, and status flags

## 🛠️ Customization for Your Manager

Your manager can easily customize:

1. **Change default lookback period** → Edit `value=7` in days_back input
2. **Change target countries** → Edit `available_locations` list
3. **Change default auto_scan/times_per_day** → Edit `value=1` and `value=72`
4. **Add new countries** → Add to `available_locations` and update regex
5. **Change color scheme** → Modify `highlight_correct_config` function

This system provides everything your manager requested:
- ✅ Configurable lookback period
- ✅ Project table display
- ✅ One-click configuration updates
- ✅ Green color coding for correct configurations
- ✅ Summary statistics showing what's already configured correctly