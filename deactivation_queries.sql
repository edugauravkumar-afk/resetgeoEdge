
-- ====================================
-- ACCOUNT DEACTIVATION DETECTION QUERIES
-- ====================================

-- 1. Find accounts that became inactive in the last 24 hours
SELECT 
    id as publisher_id,
    name as publisher_name,
    status,
    inactivity_date,
    update_time,
    status_change_reason,
    TIMESTAMPDIFF(HOUR, COALESCE(inactivity_date, update_time), NOW()) as hours_ago
FROM publishers 
WHERE status = 'INACTIVE'
  AND (
      inactivity_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
      OR (inactivity_date IS NULL AND update_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR))
  )
ORDER BY COALESCE(inactivity_date, update_time) DESC;

-- 2. Count projects under recently inactive accounts
SELECT 
    p.id as publisher_id,
    p.name as publisher_name,
    p.status as publisher_status,
    COUNT(DISTINCT gep.project_id) as total_projects,
    COUNT(DISTINCT c.id) as total_campaigns,
    COUNT(CASE WHEN c.status = 'ACTIVE' THEN 1 END) as active_campaigns,
    MAX(gep.creation_date) as latest_project_date
FROM publishers p
LEFT JOIN sp_campaigns c ON p.id = c.syndicator_id
LEFT JOIN geo_edge_projects gep ON c.id = gep.campaign_id
WHERE p.status = 'INACTIVE'
  AND (
      p.inactivity_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
      OR (p.inactivity_date IS NULL AND p.update_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR))
  )
GROUP BY p.id, p.name, p.status
HAVING total_projects > 0
ORDER BY total_projects DESC;

-- 3. Find specific projects needing reset for an account
SELECT 
    gep.project_id,
    gep.creation_date,
    c.syndicator_id,
    c.status as campaign_status,
    p.name as publisher_name
FROM geo_edge_projects gep
JOIN sp_campaigns c ON gep.campaign_id = c.id
JOIN publishers p ON c.syndicator_id = p.id
WHERE c.syndicator_id = 'REPLACE_WITH_ACCOUNT_ID'
  AND p.status = 'INACTIVE'
ORDER BY gep.creation_date DESC;

-- 4. Current status distribution
SELECT 
    status,
    COUNT(*) as account_count
FROM publishers 
GROUP BY status 
ORDER BY account_count DESC;

-- 5. Recent status changes (if using update_time as proxy)
SELECT 
    id,
    name,
    status,
    update_time,
    status_change_reason,
    TIMESTAMPDIFF(HOUR, update_time, NOW()) as hours_since_update
FROM publishers 
WHERE update_time >= DATE_SUB(NOW(), INTERVAL 48 HOUR)
  AND status = 'INACTIVE'
ORDER BY update_time DESC
LIMIT 50;
