# GeoEdge Country Projects Dashboard

Query and analyze GeoEdge projects from the **last N days** whose `locations` include **any** of a given set of country codes (default: IT, FR, DE, ES). Works with **MySQL** (PyMySQL) and **Vertica** (vertica-python).

## 🚀 Quick Start

### Web Dashboard (Recommended)
Run the interactive Streamlit dashboard:
```bash
./run_dashboard.sh
```
Or manually:
```bash
streamlit run streamlit_app.py
```

### Command Line Interface
Query projects from command line:
```bash
python query_projects.py --db mysql --days 7 --countries IT,FR,DE,ES
```

## Setup

1) Create `.env` in this folder (or edit the example below):

```
# --- GeoEdge API ---
GEOEDGE_API_KEY=your_api_key
GEOEDGE_API_BASE=https://api.geoedge.com/rest/analytics/v3

# --- Vertica Database ---
VERTICA_HOST=office-vr
VERTICA_PORT=5433
VERTICA_USER=username
VERTICA_PASSWORD=password
VERTICA_DB=database_name

# --- MySQL Database ---
MYSQL_HOST=proxy
MYSQL_PORT=6033
MYSQL_USER=username
MYSQL_PASSWORD=password
MYSQL_DB=database_name
MYSQL_AUTH_PLUGIN=mysql_clear_password
```

2) Install dependencies:
```bash
pip install -r requirements.txt
```

## 🌐 Streamlit Dashboard Features

- **Interactive Web Interface**: Filter and explore data in your browser
- **Real-time Filtering**: Filter by countries, status, and other criteria
- **API Integration**: Fetch `auto_scan` and `times_per_day` details from GeoEdge API
- **Export Options**: Download results as CSV or JSON
- **Progress Tracking**: Visual progress bars for API calls
- **Responsive Design**: Works on desktop and mobile

### Dashboard Usage
1. Configure database and filters in the sidebar
2. Select target countries (IT, FR, DE, ES, etc.)
3. Set date range and result limits
4. Click "Query Projects" to fetch data
5. Use filters to refine results
6. Download data in your preferred format

## 📊 Command Line Usage

### Basic Examples

MySQL (default):
```bash
python query_projects.py --db mysql --days 7 --countries IT,FR,DE,ES
```

Vertica:
```bash
python query_projects.py --db vertica --days 7 --countries IT,FR,DE,ES
```

Export to Excel:
```bash
python query_projects.py --excel results.xlsx
```

Output as JSON:
```bash
python query_projects.py --json
```

Limit rows (server-side):
```bash
python query_projects.py --limit 500
```

### Advanced Examples

Query last 14 days with more countries:
```bash
python query_projects.py --days 14 --countries IT,FR,DE,ES,UK --excel detailed_report.xlsx
```

JSON output for API integration:
```bash
python query_projects.py --json --limit 100 > projects.json
```

## 🔍 What it does

- Loads DB credentials from `.env`
- Queries projects with **ACTIVE** instruction status in the last N days
- Filters `trc.geo_edge_projects` joined with `trc.sp_campaign_inventory_instructions` where:
  - `instruction_status = 'ACTIVE'`
  - `creation_date >= NOW() - INTERVAL N DAYS`
  - `locations` (comma-separated codes) includes any of the requested countries
- Shows `SNo, project_id, campaign_id, locations, creation_date, instruction_status, auto_scan, times_per_day`
- Fetches additional project details from GeoEdge API
- Can export results to Excel format (.xlsx)

## 📁 Output Columns

| Column | Description |
|--------|-------------|
| **SNo** | Serial number (1, 2, 3, ...) |
| **project_id** | Unique project identifier |
| **campaign_id** | Campaign identifier |
| **locations** | Target country codes (e.g., "FR", "IT,DE") |
| **creation_date** | When the project was created |
| **instruction_status** | Campaign instruction status (ACTIVE) |
| **auto_scan** | Auto-scan enabled status (0/1) |
| **times_per_day** | Scans per day frequency |

## 🔧 Technical Notes

- Uses **comma-safe** regex to avoid partial matches: `',(IT|FR|DE|ES),'`
- The regex and timestamp are **bound parameters** (SQL injection safe)
- For MySQL: uses `REGEXP` operator and `DATE_SUB(NOW(), INTERVAL N DAY)`
- For Vertica: uses `REGEXP_LIKE` and `NOW() - INTERVAL 'N DAYS'`
- API calls are cached in Streamlit for better performance
- Progress bars show API fetching status

## 🛠️ Tools Included

1. **`streamlit_app.py`** - Interactive web dashboard
2. **`query_projects.py`** - Command-line query tool
3. **`run_dashboard.sh`** - Quick start script for dashboard
4. **`geoedge_projects/client.py`** - GeoEdge API client
5. **`alert_chunk_tester.py`** - Standalone alert coverage tester

### Alert Coverage Tester

Use `alert_chunk_tester.py` to verify that GeoEdge returned alerts for every chunk in a date window and to capture a JSON report that highlights any missing days. Example:

```bash
.venv/bin/python alert_chunk_tester.py 2025-08-26 2025-11-24 \
  --chunk-days 15 \
  --output chunk_report.json
```

The script walks the range in 15-day windows (configurable), counts alerts per chunk, and writes `chunk_report.json` with fields like `missing_chunks` so you can refetch only the uncovered ranges.

## 🔄 Auto-Scan Management

For updating project auto-scan settings:
```bash
python update_autoscan.py --check project_id
python update_autoscan.py project_id --times 72 --auto 1
```

> Valid `times_per_day` values: 1,2,3,4,6,8,12,24,48,72,96,120,144,168,192,216,240,480,720
# resetgeoEdge
