# Daily LP Alerts Report - Working Logic

## 📋 System Overview

The Daily LP Alerts Report is an **automated monitoring system** that:
1. Finds campaigns targeting English countries (US, GB, CA, AU, NZ, IE)
2. Fetches Landing Page (LP) change alerts from GeoEdge API
3. Filters alerts for LATAM & Greater China accounts only
4. Sends a daily HTML email report with clickable alert links

**Scheduler:** Runs daily at **08:00 UTC**

---

## 🔄 Complete Workflow

### **Step 1️⃣: Fetch English-Targeting Campaigns**

**What it does:**
- Queries MySQL database (`trc.geo_edge_projects`)
- Finds campaigns with target locations matching English countries

**SQL Query Logic:**
```
SELECT campaign_id, project_name
FROM trc.geo_edge_projects
WHERE JSON_EXTRACT(locations, '$.target_locations') 
      CONTAINS ANY OF ('US', 'GB', 'CA', 'AU', 'NZ', 'IE')
```

**Output:** List of 683,693+ campaign IDs targeting English countries

---

### **Step 2️⃣: Fetch Landing Page Alerts from GeoEdge API**

**What it does:**
- Calls GeoEdge REST API endpoint: `https://api.geoedge.com/rest/analytics/v3/alerts/history`
- Fetches all alerts from the last **24 hours**
- Filters for LP (Landing Page) alerts only

**Parameters:**
- Time range: Last 24 hours
- Alert type: "LP Change", "Landing Page Change", etc.
- Limit: 5,000 alerts per page, up to 100 pages

**API Response includes:**
```json
{
  "alert_name": "LP Change",
  "campaign_id": 46193778,
  "alert_details_url": "https://site.geoedge.com/analyticsv2/alertshistory/{id}/...",
  "id": "unique-alert-id",
  "timestamp": "2025-12-15T12:00:00Z"
}
```

**Output:** List of real LP alerts (e.g., 4,383 alerts in last 7 days)

---

### **Step 3️⃣: Match Alerts to English Campaigns**

**What it does:**
- Compares alert's `campaign_id` with English-targeting campaigns from Step 1
- Keeps only alerts that match English-targeting campaigns
- Discards alerts for campaigns NOT targeting English countries

**Logic:**
```python
for alert in lp_alerts:
    campaign_id = alert.get('campaign_id')
    if campaign_id in english_campaigns:
        matched_alerts.append(alert)
```

**Output:** Filtered list of alerts from English-targeting campaigns

---

### **Step 4️⃣: Fetch Account IDs for Matched Campaigns**

**What it does:**
- For each matched campaign, finds all advertiser accounts
- Queries MySQL: `trc.geo_edge_projects` → accounts & locations

**SQL Query:**
```sql
SELECT DISTINCT advertiser_id, locations
FROM trc.geo_edge_projects
WHERE campaign_id IN (matched_campaign_ids)
```

**Output:** Mapping of campaign_id → [accounts with target locations]

---

### **Step 5️⃣: Fetch Account Countries**

**What it does:**
- For each account ID, fetches the country/region code
- Queries MySQL: `trc.account_countries`

**SQL Query:**
```sql
SELECT account_id, country_code
FROM trc.account_countries
WHERE account_id IN (all_account_ids)
```

**Output:** Mapping of account_id → country code (e.g., CN, BR, MX, HK)

---

### **Step 6️⃣: Filter for LATAM & Greater China**

**What it does:**
- Keeps only accounts in target regions:
  - **LATAM:** Mexico (MX), Argentina (AR), Brazil (BR), Chile (CL), Colombia (CO), Peru (PE)
  - **Greater China:** China (CN), Hong Kong (HK), Taiwan (TW), Macau (MO)

**Logic:**
```python
TARGET_REGIONS = LATAM_COUNTRIES | GREATER_CHINA_COUNTRIES

for campaign_id, accounts in campaign_to_accounts.items():
    for account in accounts:
        country = account_countries.get(account.id)
        if country in TARGET_REGIONS:
            # This account qualifies!
            filtered_data.append({
                'account_id': account.id,
                'country': country,
                'campaign_id': campaign_id,
                'alert_link': alert.alert_details_url,
                ...
            })
```

**Output:** Final data set of alerts for LATAM & Greater China accounts

---

### **Step 7️⃣: Extract Alert Links**

**What it does:**
- For each alert, extracts the clickable link with priority order:

**Priority Order:**
1. **Primary:** `alert_details_url` from API response
   - Format: `https://site.geoedge.com/analyticsv2/alertshistory/{alert_id}/1/off/`
   - This is the **real alert history page** showing LP change details

2. **Fallback 1:** Check alternative URL fields (`url`, `alert_url`, `link`)

3. **Fallback 2:** Construct from `alert_id` if available
   - `https://site.geoedge.com/analyticsv2/alertshistory/{alert_id}/1`

4. **Fallback 3:** Campaign analytics page
   - `https://site.geoedge.com/analyticsv2?filter=campaign:{campaign_id}`

**Code:**
```python
if "alert_details_url" in alert_data and alert_data["alert_details_url"]:
    alert_link = alert_data["alert_details_url"]  # ✅ REAL LINK
elif alert_data.get("alert_id"):
    alert_link = f"https://site.geoedge.com/analyticsv2/alertshistory/{alert_id}/1"
else:
    alert_link = f"https://site.geoedge.com/analyticsv2?filter=campaign:{campaign_id}"
```

---

### **Step 8️⃣: Generate HTML Report**

**What it does:**
- Creates professional HTML email with blue theme (#054164)
- Two tables: LATAM accounts & Greater China accounts
- Each row is clickable with "View Alert" link

**HTML Structure:**
```html
<body style="background: #054164; color: white;">
  <h1>Daily LP Alerts Report</h1>
  
  <!-- Summary Section -->
  <div class="summary">
    🌎 LATAM: 8 alerts | 🏮 Greater China: 34 alerts
  </div>
  
  <!-- LATAM Table -->
  <h2>LATAM Accounts</h2>
  <table>
    <tr>
      <th>Account ID</th>
      <th>Country</th>
      <th>Campaign ID</th>
      <th>Target Locations</th>
      <th>Alert Type</th>
      <th>Alert Link</th>
    </tr>
    <tr>
      <td>1822556</td>
      <td>BR</td>
      <td>47403529</td>
      <td>US</td>
      <td>LP CHANGE</td>
      <td><a href="alert_details_url">View Alert</a></td>
    </tr>
    ...
  </table>
  
  <!-- Greater China Table -->
  <h2>Greater China Accounts</h2>
  <table>
    ...
  </table>
  
  <!-- Footer -->
  <div class="footer">
    Report generated: 2025-12-15
  </div>
</body>
```

---

### **Step 9️⃣: Send Email**

**What it does:**
- Sends HTML email via SMTP
- To: gaurav.k@taboola.com
- CC: ads-anti-fraud@taboola.com
- Server: ildcsmtp.office.taboola.com:25

**Email Details:**
```python
msg = MIMEMultipart('alternative')
msg['Subject'] = f"Daily LP Alerts - 2025-12-15 - LATAM (8) | Greater China (34)"
msg['From'] = "Daily-LP-Alerts@taboola.com"
msg['To'] = "gaurav.k@taboola.com"
msg['Cc'] = "ads-anti-fraud@taboola.com"

msg.attach(MIMEText(html_report, 'html'))

smtp = smtplib.SMTP(server, port)
smtp.sendmail(from_email, recipients, msg.as_string())
```

---

### **Step 🔟: Save to CSV**

**What it does:**
- Exports all alert data to CSV file for records
- File: `latam_greater_china_lp_alerts_24h.csv`

**CSV Columns:**
```
account_id, country, region, campaign_id, locations, alert_name, alert_id, alert_link
1822556, BR, LATAM, 47403529, US, LP Change, xyz123, https://site.geoedge.com/...
```

---

## 📊 Data Flow Diagram

```
MySQL Database (campaigns)
       ↓
Step 1: Fetch English-targeting campaigns
       ↓
GeoEdge API
       ↓
Step 2: Fetch LP alerts (last 24h)
       ↓
Step 3: Match alerts to English campaigns
       ↓
Step 4: Fetch account IDs for matched campaigns
       ↓
MySQL Database (accounts)
       ↓
Step 5: Fetch account countries
       ↓
Step 6: Filter for LATAM & Greater China
       ↓
Step 7: Extract alert links from API
       ↓
Step 8: Generate HTML report (blue theme)
       ↓
Step 9: Send email via SMTP
       ↓
Step 10: Save to CSV
```

---

## 🎯 Key Features

### **Blue Theme Styling**
- Background gradient: `#054164` → `#0a2d47`
- Text color: White
- Links: Blue (#054164) with underline
- Professional appearance with shadow effects

### **Alert Link Priority**
- Real `alert_details_url` from GeoEdge API (shows alert details)
- Fallback URLs for robustness
- All links open in new tab (`target="_blank"`)

### **Error Handling**
- Graceful degradation: Works even if some data is missing
- "No alerts" email with proper styling
- Comprehensive logging for debugging
- Retry logic for API timeouts

### **Filtering Logic**
- English countries: US, GB, CA, AU, NZ, IE
- LATAM: MX, AR, BR, CL, CO, PE
- Greater China: CN, HK, TW, MO
- Only reports on LATAM & Greater China accounts

---

## ⏰ Scheduler

**Runs automatically every day at 08:00 UTC**

```python
schedule.every().day.at("08:00").do(generate_and_send_alerts)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 📝 Sample Report

### **Email Subject:**
```
Daily LP Alerts - 2025-12-15 - LATAM (8) | Greater China (34)
```

### **Email Content:**

```
Daily LP Alerts Report

📊 Summary
🌎 LATAM Accounts: 8 alerts
🏮 Greater China Accounts: 34 alerts
Total: 42 LP change alerts detected

LATAM Accounts
[Table with 8 rows]

Greater China Accounts  
[Table with 34 rows - each with "View Alert" link]

Footer: Report generated on 2025-12-15
For questions, contact ads-anti-fraud@taboola.com
```

---

## 🔗 Alert Link Example

When user clicks "View Alert", they go to:
```
https://site.geoedge.com/analyticsv2/alertshistory/134e4522f7317/1/off/
```

This page shows:
- ✅ Landing Page changes (old → new URL)
- ✅ Device information (Chrome, Firefox, etc.)
- ✅ Location of capture (US, UK, etc.)
- ✅ Timeline of changes
- ✅ Project/campaign details

---

## 💾 Environment Variables Required

```bash
# Database
MYSQL_HOST=
MYSQL_PORT=6033
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DB=

# GeoEdge API
GEOEDGE_API_KEY=
GEOEDGE_API_BASE=https://api.geoedge.com/rest/analytics/v3

# Email
SMTP_SERVER=ildcsmtp.office.taboola.com
SMTP_PORT=25
FROM_EMAIL=Daily-LP-Alerts@taboola.com
RECIPIENTS=gaurav.k@taboola.com
CC_RECIPIENTS=ads-anti-fraud@taboola.com
```

---

## ✨ Summary

The system is a **fully automated LP alerts monitoring pipeline** that:
- ✅ Fetches real LP alerts from GeoEdge API
- ✅ Intelligently matches them to campaign data
- ✅ Filters for LATAM & Greater China accounts
- ✅ Extracts real alert detail links from API
- ✅ Generates professional blue-themed HTML emails
- ✅ Sends via SMTP with proper formatting
- ✅ Saves data to CSV for records
- ✅ Runs automatically on schedule

**Status:** Ready for production deployment! 🚀
