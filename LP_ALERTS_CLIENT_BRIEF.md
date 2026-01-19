# Daily LP Alerts Report - Client Brief for Lihi

**Prepared by:** Gaurav K  
**Date:** December 15, 2025  
**System Status:** ✅ Ready for Production

---

## 📋 Executive Summary

The Daily LP Alerts Report is an **automated monitoring system** that detects Landing Page (LP) changes in campaigns and sends daily email reports. The system focuses specifically on **LATAM and Greater China accounts** for campaigns targeting English-speaking countries.

**Key Benefit:** Proactive alerts about LP changes that could impact campaign performance and compliance.

---

## 🎯 What Does It Monitor?

### **Scope**
- **Campaigns:** All campaigns targeting English countries (US, GB, CA, AU, NZ, IE)
- **Alert Type:** Landing Page (LP) changes
- **Accounts:** LATAM & Greater China only

### **Target Regions**
- **LATAM:** Mexico (MX), Argentina (AR), Brazil (BR), Chile (CL), Colombia (CO), Peru (PE)
- **Greater China:** China (CN), Hong Kong (HK), Taiwan (TW), Macau (MO)

### **Data Source**
- GeoEdge API: Real-time landing page change alerts
- Database: Campaign and account metadata

---

## ⏰ When Are Emails Sent?

### **Production Schedule**
- **Frequency:** Daily
- **Time:** **08:00 UTC** (3:00 AM EST / 12:00 PM IST)
- **Days:** Monday - Sunday (every day)

### **What Triggers an Email?**
1. ✅ **LP alerts detected** → Full report with data table
2. ✅ **No LP alerts** → "No alerts" notification (styled email)
3. ✅ **System error** → Error notification with details

### **Email Delivery**
- SMTP Server: ildcsmtp.office.taboola.com
- From: Daily-LP-Alerts@taboola.com
- To: gaurav.k@taboola.com, ariel@taboola.com
- CC: ads-anti-fraud@taboola.com
- Transport: Unencrypted SMTP (port 25)

---

## 📧 Current Email Format

### **Email Subject (When Alerts Found)**
```
Daily LP Alerts - 2025-12-15 - LATAM (8) | Greater China (34)
```
- Date: Current date (YYYY-MM-DD)
- Alert counts for each region

### **Email Subject (No Alerts)**
```
Daily LP Alerts Report - No New Alerts
```

---

## 📊 Email Body Structure

### **1. Visual Design**
- **Background:** Blue gradient (#054164 to #0a2d47)
- **Text:** White color for contrast
- **Styling:** Professional, clean, easy to read
- **Theme:** Consistent with company branding

### **2. Header Section**
```
Daily LP Alerts Report

Summary
🌎 LATAM Accounts: 8 alerts
🏮 Greater China Accounts: 34 alerts
Total: 42 LP change alerts detected
```

### **3. LATAM Accounts Table**
| Account ID | Country | Campaign ID | Target Locations | Alert Type | Alert Link |
|-----------|---------|------------|------------------|-----------|-----------|
| 1822556 | BR | 47403529 | US | LP CHANGE | [View Alert] |
| 1902030 | BR | 47492180 | BR,IN,CA | LP CHANGE | [View Alert] |
| ... | ... | ... | ... | ... | ... |

### **4. Greater China Accounts Table**
| Account ID | Country | Campaign ID | Target Locations | Alert Type | Alert Link |
|-----------|---------|------------|------------------|-----------|-----------|
| 1343639 | CN | 46193778 | AU,US,CA | LP CHANGE | [View Alert] |
| 1535322 | HK | 47581302 | US | LP CHANGE | [View Alert] |
| ... | ... | ... | ... | ... | ... |

### **5. Alert Links**
- **Clickable:** "View Alert" button for each row
- **Destination:** GeoEdge alert history page
- **Opens in:** New browser tab
- **Shows:** 
  - Specific LP change details
  - Old → new URL comparison
  - Device information (browser, OS)
  - Location of change
  - Timeline of changes
  - Project/campaign details

### **6. Footer**
```
Report generated on 2025-12-15
For questions, contact ads-anti-fraud@taboola.com
```

---

## 🔄 Complete Workflow (10 Steps)

### **Step 1: Fetch English-Targeting Campaigns**
- Query database for campaigns targeting English countries
- Result: 683,693+ campaigns

### **Step 2: Fetch LP Alerts from GeoEdge API**
- Call GeoEdge REST API for last 24 hours
- Filter for "Landing Page Change" alerts
- Result: Real alerts from GeoEdge system

### **Step 3: Match Alerts to English Campaigns**
- Keep only alerts from English-targeting campaigns
- Discard alerts for other campaigns

### **Step 4: Fetch Account IDs**
- Find all advertiser accounts for matched campaigns
- Get target locations for each campaign

### **Step 5: Fetch Account Countries**
- Get country/region code for each account
- Determine if account is in LATAM or Greater China

### **Step 6: Filter for LATAM & Greater China**
- Keep only accounts in target regions
- Discard other regions

### **Step 7: Extract Alert Links**
- Get real alert details URL from GeoEdge API
- Priority: alert_details_url → fallback URLs → constructed URL

### **Step 8: Generate HTML Report**
- Create professional blue-themed email
- Build two tables (LATAM and Greater China)
- Add clickable alert links

### **Step 9: Send Email**
- SMTP to recipients and CC addresses
- HTML formatted email
- Subject line with region counts

### **Step 10: Save to CSV**
- Export data to file: `latam_greater_china_lp_alerts_24h.csv`
- For records and analysis

---

## 📈 Sample Report Statistics

### **From Recent Test**
- **Total Alerts Scanned:** 10,000+
- **LP Alerts Found:** 4,383
- **Matched to English Campaigns:** Variable
- **LATAM Accounts:** 5
- **Greater China Accounts:** 37
- **Total Reported:** 42

---

## 🔗 Alert Link Example

When user clicks "View Alert", they navigate to:
```
https://site.geoedge.com/analyticsv2/alertshistory/{alert_id}/1/off/
```

### **Page Shows:**
- ✅ Landing Page changes (what changed)
- ✅ URLs (old URL → new URL)
- ✅ Device info (Chrome, Safari, etc.)
- ✅ Location (US, UK, Germany, etc.)
- ✅ Timestamp (when change was detected)
- ✅ Project/campaign details
- ✅ Timeline of changes

---

## 💾 Data Export

### **CSV File**
- **Name:** latam_greater_china_lp_alerts_24h.csv
- **Location:** Project root directory
- **Updated:** Daily after email sent
- **Columns:**
  - account_id
  - country
  - region (LATAM or Greater China)
  - campaign_id
  - locations (target locations)
  - alert_name (LP Change)
  - alert_id
  - alert_link (clickable URL)

---

## ⚙️ System Configuration

### **Database Connection**
- Host: proxysql-office.taboolasyndication.com
- Port: 6033
- Database: trc
- Tables Used:
  - trc.geo_edge_projects (campaigns)
  - trc.account_countries (account regions)

### **API Configuration**
- Provider: GeoEdge
- Endpoint: https://api.geoedge.com/rest/analytics/v3/alerts/history
- Authentication: API Key
- Rate Limit: 100 pages, 5,000 alerts per page

### **Email Configuration**
- SMTP Server: ildcsmtp.office.taboola.com
- Port: 25 (unencrypted)
- Timeout: 30 seconds
- Retry: Automatic on failure

---

## ✨ Current Features

### **✅ Implemented**
- ✅ Daily automated scheduling (08:00 UTC)
- ✅ Real-time alert fetching from GeoEdge
- ✅ Multi-region filtering (LATAM & Greater China)
- ✅ Blue-themed HTML emails
- ✅ Clickable alert links
- ✅ Professional report layout
- ✅ CSV export for records
- ✅ Error handling and logging
- ✅ SMTP delivery to multiple recipients
- ✅ CC field for alerts team

---

## 📝 REQUEST FOR CLIENT FEEDBACK

### **Dear Lihi,**

The Daily LP Alerts Report system is complete and ready for deployment. Before we go live, we'd like your feedback on the following:

### **1. Email Subject Line**
**Current:**
```
Daily LP Alerts - 2025-12-15 - LATAM (8) | Greater China (34)
```
**Questions:**
- Is this clear and informative?
- Would you prefer a different format?
- Should we add urgency indicators?
- Any preferred emoji or branding?

### **2. Email Body Content**
**Current Layout:**
- Summary section (counts by region)
- LATAM table
- Greater China table
- Footer with contact info

**Questions:**
- Is the layout clear and readable?
- Should we add more sections (e.g., methodology, definitions)?
- Would you like a visual dashboard or just tables?
- Should we add alert severity levels?

### **3. Table Columns**
**Current Columns:**
1. Account ID
2. Country
3. Campaign ID
4. Target Locations
5. Alert Type (LP CHANGE)
6. Alert Link (clickable)

**Questions:**
- Are all columns necessary?
- Should we add more details (e.g., alert timestamp, LP URL)?
- Would you like to group by country or region?
- Should we add alert severity or priority?

### **4. Alert Link Behavior**
**Current:**
- Links to GeoEdge alert history page
- Shows LP change details (old → new URL)
- Opens in new tab

**Questions:**
- Is this the right destination?
- Would you prefer different alert page?
- Should we add additional context or metadata?

### **5. Report Frequency & Timing**
**Current:**
- Daily at 08:00 UTC (3:00 AM EST)
- Every day (including weekends)

**Questions:**
- Is 08:00 UTC the right time?
- Should we exclude weekends?
- Should we provide multiple formats (HTML, PDF, Excel)?
- Would you like hourly or real-time alerts instead?

### **6. Recipients & Distribution**
**Current:**
- To: gaurav.k@taboola.com, ariel@taboola.com
- CC: ads-anti-fraud@taboola.com

**Questions:**
- Are the recipients correct?
- Should we add/remove anyone?
- Should we create distribution lists?
- Should we send to Slack/Teams instead?

### **7. Visual Design & Branding**
**Current:**
- Blue gradient background (#054164)
- White text
- Professional styling

**Questions:**
- Do you like the blue color scheme?
- Should we add company logo?
- Any specific branding guidelines?
- Should we add company colors/theme?

### **8. Additional Features**
**Questions:**
- Would you like alert severity/priority levels?
- Should we add trend analysis (comparing to previous days)?
- Would you like filters (by country, campaign type, etc.)?
- Should we include recommended actions?
- Would you like performance metrics or KPIs?

### **9. Data & Privacy**
**Questions:**
- Is it okay to include account IDs and campaign IDs?
- Should we encrypt or anonymize any data?
- How long should we retain CSV records?
- Any compliance or security concerns?

### **10. Testing & Validation**
**Questions:**
- Should we do a pilot run with limited accounts?
- What validation do you need before full launch?
- Should we set up alerts for system failures?
- What's the rollback plan if issues arise?

---

## 📞 Next Steps

1. **Review:** Please review this document and the sample emails
2. **Feedback:** Provide feedback on the questions above
3. **Adjustments:** We'll implement any requested changes
4. **Testing:** Run final tests with real data
5. **Deployment:** Schedule production launch

---

## 📎 Attachments

- Sample Email #1: With alerts (42 rows)
- Sample Email #2: No alerts found
- System Logic Document (LP_ALERTS_LOGIC.md)
- Production Code (main.py)

---

## 📊 Success Metrics

Once deployed, we'll monitor:
- ✅ Email delivery rate (target: 100%)
- ✅ Alert accuracy (real LP changes detected)
- ✅ System uptime (target: 99.9%)
- ✅ Processing time (target: < 5 minutes)
- ✅ User engagement (click rates on alert links)

---

## 🚀 Ready to Launch

The system is **production-ready** and awaiting your feedback before full deployment.

**Questions or concerns?** Please reach out to Gaurav K.

---

**System Status:** ✅ Code Complete | ⏳ Awaiting Client Approval | 🚀 Ready for Deployment
