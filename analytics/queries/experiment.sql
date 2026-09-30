-- Per-variant results for the onboarding test:
-- tutorial completion (primary metric) and D7 retention (guardrail).

WITH last_day AS (
    SELECT MAX(date(ts)) AS d FROM clean_events
),
completed AS (
    SELECT DISTINCT player_id FROM clean_events WHERE event = 'tutorial_complete'
),
d7 AS (
    SELECT DISTINCT e.player_id
    FROM clean_events e
    JOIN players p ON p.player_id = e.player_id
    WHERE e.event = 'session_start'
      AND date(e.ts) = date(p.install_day, '+7 days')
)
SELECT p.variant,
       COUNT(*)                                     AS players,
       COUNT(c.player_id)                           AS completed_tutorial,
       SUM(date(p.install_day, '+7 days') <= l.d)   AS d7_eligible,
       SUM(date(p.install_day, '+7 days') <= l.d AND d.player_id IS NOT NULL) AS d7_retained
FROM players p
CROSS JOIN last_day l
LEFT JOIN completed c ON c.player_id = p.player_id
LEFT JOIN d7 d        ON d.player_id = p.player_id
GROUP BY p.variant
ORDER BY p.variant;
