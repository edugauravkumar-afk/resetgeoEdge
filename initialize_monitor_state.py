#!/usr/bin/env python3
"""
Initialize the daily monitor state with the 197 accounts already processed on 2026-01-20
This prevents re-processing the accounts that were already reset today.
"""

import json
from datetime import datetime

# The 197 inactive accounts that were already reset to Manual Mode today
ALREADY_PROCESSED_ACCOUNTS = [
    1352198, 1950734, 1937426, 1860125, 1823262, 1944607, 1827872, 1956903, 1943081, 1947177,
    1889326, 1943602, 1959374, 1606199, 1949239, 1803836, 1925694, 1925696, 1943621, 1907271,
    1949258, 1958987, 1948754, 1929299, 1905236, 1911893, 1896030, 1929315, 1908837, 1936999,
    1943663, 1943664, 1947761, 1886322, 1904243, 1904244, 1904245, 1923699, 1857143, 1904248,
    1904249, 1947765, 1894525, 1938564, 1951366, 1909385, 1882251, 1912972, 1928843, 1912974,
    1938059, 1941131, 1938066, 1899166, 1940640, 1947296, 1950370, 1781411, 1941156, 1941669,
    1947304, 1936044, 1907885, 1937588, 1907383, 1872062, 1878208, 1920193, 1920194, 1920197,
    1826503, 1920200, 1927367, 1941195, 1941196, 1915600, 1925332, 1929951, 1951979, 1894125,
    1899760, 1894130, 1957113, 1945850, 1939709, 1881854, 1939712, 1939713, 1945348, 1820428,
    1346317, 1424656, 1939729, 1777430, 1883417, 1425690, 1881883, 1766692, 1940262, 1935145,
    1939247, 1959729, 1919282, 1948980, 1929015, 1952057, 1959226, 1907516, 1923392, 1958722,
    1511236, 1833285, 1897286, 1890632, 1959240, 1928013, 1939790, 1847119, 1924943, 1945937,
    1909587, 1792854, 1945942, 1924955, 1842014, 1894752, 1924961, 1881443, 1833317, 1823078,
    1939814, 1939816, 1708395, 1916785, 1935730, 1929079, 1833860, 1942405, 1939334, 1914250,
    1943951, 1833361, 1941905, 1929107, 1909654, 1925530, 1859995, 1925532, 1927073, 1927074,
    1671075, 1951144, 1958830, 1908656, 1895857, 1874354, 1942452, 1896885, 1910198, 1921462,
    1927093, 1943993, 1895867, 1936827, 1861571, 1908683, 1934283, 1874381, 1934285, 1901007,
    1933775, 1933777, 1934286, 1936843, 1948109, 1920469, 1949134, 1942999, 1958866, 1644506,
    1952731, 1946080, 1912802, 1946084, 1947109, 1949157, 1895912, 1935336, 1945580, 1957360,
    1958388, 1936885, 1607160, 1939963, 1889788, 1944573, 1913854
]

state_file = 'daily_monitor_state.json'

initial_state = {
    "inactive_accounts": ALREADY_PROCESSED_ACCOUNTS,
    "last_check": "2026-01-20T00:00:00",
    "stats": {
        "run_timestamp": "2026-01-20T00:00:00",
        "total_configured_accounts": 3532,
        "total_projects_configured": 16407,
        "total_inactive_accounts": 197,
        "total_active_accounts": 3335,
        "new_inactive_accounts_24h": 197,
        "projects_reset_to_manual": 2021,
        "reset_success_count": 2021,
        "reset_failure_count": 0,
        "remaining_active_accounts": 3335,
        "remaining_active_projects": 14386
    }
}

print("Initializing daily monitor state file...")
print(f"Adding {len(ALREADY_PROCESSED_ACCOUNTS)} already-processed inactive accounts")

with open(state_file, 'w') as f:
    json.dump(initial_state, f, indent=2)

print(f"✅ State file created: {state_file}")
print()
print("Summary:")
print(f"  • Inactive accounts marked as processed: {len(ALREADY_PROCESSED_ACCOUNTS)}")
print(f"  • Last check timestamp: 2026-01-20T00:00:00")
print(f"  • Projects already reset: 2,021")
print()
print("Next run will only process accounts that become NEWLY inactive!")
