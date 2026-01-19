-- SQL Queries to Find When Accounts Were Deactivated
-- Run these directly in your MySQL client to investigate account deactivation timing

-- Query 1: Check for accounts that have recent projects but are inactive
-- This suggests they were active recently but became inactive
SELECT 
    p.syndicator_id,
    p.status,
    COUNT(gep.project_id) as total_projects,
    MIN(gep.date_created) as first_project_date,
    MAX(gep.date_created) as latest_project_date,
    DATEDIFF(NOW(), MAX(gep.date_created)) as days_since_last_project,
    -- If they have projects in last 30 days but are inactive, they likely became inactive recently
    CASE 
        WHEN MAX(gep.date_created) >= DATE_SUB(NOW(), INTERVAL 30 DAYS) THEN 'RECENTLY_DEACTIVATED'
        WHEN MAX(gep.date_created) >= DATE_SUB(NOW(), INTERVAL 90 DAYS) THEN 'POSSIBLY_RECENT'
        ELSE 'OLD_INACTIVE'
    END as deactivation_likelihood
FROM publishers p
JOIN geo_edge_projects gep ON p.syndicator_id = gep.syndicator_id
WHERE p.status IN ('inactive', 'paused', 'suspended', 'frozen')
GROUP BY p.syndicator_id, p.status
ORDER BY latest_project_date DESC;

-- Query 2: Find inactive accounts with projects created in last 7 days (definitely recently deactivated)
SELECT 
    p.syndicator_id,
    p.status,
    COUNT(gep.project_id) as projects_last_7_days,
    MAX(gep.date_created) as latest_project_date,
    'ALERT: Became inactive after creating projects' as status_note
FROM publishers p
JOIN geo_edge_projects gep ON p.syndicator_id = gep.syndicator_id
WHERE p.status IN ('inactive', 'paused', 'suspended', 'frozen')
AND gep.date_created >= DATE_SUB(NOW(), INTERVAL 7 DAYS)
GROUP BY p.syndicator_id, p.status
ORDER BY latest_project_date DESC;

-- Query 3: Check project configuration for inactive accounts
-- Shows which projects need to be reset to (0,0)
SELECT 
    p.syndicator_id,
    p.status,
    COUNT(*) as total_projects,
    SUM(CASE WHEN gep.auto_scan = 1 THEN 1 ELSE 0 END) as projects_with_auto_scan,
    SUM(CASE WHEN gep.times_per_day > 0 THEN 1 ELSE 0 END) as projects_with_daily_scans,
    SUM(CASE WHEN gep.auto_scan = 0 AND gep.times_per_day = 0 THEN 1 ELSE 0 END) as properly_configured,
    (COUNT(*) - SUM(CASE WHEN gep.auto_scan = 0 AND gep.times_per_day = 0 THEN 1 ELSE 0 END)) as needs_reset
FROM publishers p
JOIN geo_edge_projects gep ON p.syndicator_id = gep.syndicator_id
WHERE p.status IN ('inactive', 'paused', 'suspended', 'frozen')
GROUP BY p.syndicator_id, p.status
HAVING needs_reset > 0
ORDER BY needs_reset DESC;

-- Query 4: Check if there are any audit/log tables for status changes
-- This query helps identify if there are audit tables we can use
SHOW TABLES LIKE '%audit%';
SHOW TABLES LIKE '%log%';
SHOW TABLES LIKE '%history%';

-- Query 5: If you have campaign data, check for activity patterns
-- This can help estimate when accounts stopped being active
SELECT 
    p.syndicator_id,
    p.status,
    COUNT(DISTINCT sp.id) as total_campaigns,
    MIN(sp.date_created) as first_campaign,
    MAX(sp.date_created) as last_campaign,
    DATEDIFF(NOW(), MAX(sp.date_created)) as days_since_last_campaign,
    CASE 
        WHEN MAX(sp.date_created) >= DATE_SUB(NOW(), INTERVAL 30 DAYS) THEN 'ACTIVE_RECENTLY'
        WHEN MAX(sp.date_created) >= DATE_SUB(NOW(), INTERVAL 90 DAYS) THEN 'SEMI_RECENT'
        ELSE 'LONG_INACTIVE'
    END as activity_level
FROM publishers p
LEFT JOIN sp_campaigns sp ON p.syndicator_id = sp.syndicator_id
WHERE p.status IN ('inactive', 'paused', 'suspended', 'frozen')
GROUP BY p.syndicator_id, p.status
ORDER BY last_campaign DESC
LIMIT 50;

-- Query 6: Create a baseline for tracking future changes
-- Save this result to compare with future runs
CREATE TABLE IF NOT EXISTS account_status_tracking (
    check_date DATE,
    syndicator_id INT,
    status VARCHAR(50),
    project_count INT,
    PRIMARY KEY (check_date, syndicator_id)
);

-- Insert current status (run this daily to track changes)
INSERT INTO account_status_tracking (check_date, syndicator_id, status, project_count)
SELECT 
    CURDATE(),
    p.syndicator_id,
    p.status,
    COUNT(gep.project_id)
FROM publishers p
LEFT JOIN geo_edge_projects gep ON p.syndicator_id = gep.syndicator_id
WHERE p.syndicator_id IN (
    SELECT DISTINCT syndicator_id 
    FROM geo_edge_projects 
    WHERE date_created >= DATE_SUB(NOW(), INTERVAL 90 DAYS)
)
GROUP BY p.syndicator_id, p.status
ON DUPLICATE KEY UPDATE 
    status = VALUES(status),
    project_count = VALUES(project_count);

-- Query to find accounts that changed status (run after baseline exists)
SELECT 
    t1.syndicator_id,
    t1.status as previous_status,
    t2.status as current_status,
    t1.check_date as previous_check,
    t2.check_date as current_check,
    t2.project_count
FROM account_status_tracking t1
JOIN account_status_tracking t2 ON t1.syndicator_id = t2.syndicator_id
WHERE t1.check_date = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
AND t2.check_date = CURDATE()
AND t1.status != t2.status
AND t2.status IN ('inactive', 'paused', 'suspended', 'frozen')
ORDER BY t2.syndicator_id;