-- Ordered onboarding funnel. A player only counts for a step if they also
-- did every earlier step, in order.

WITH firsts AS (
    SELECT p.player_id,
           p.installed_at,
           MIN(CASE WHEN e.event = 'tutorial_start'    THEN e.ts END) AS tutorial_start,
           MIN(CASE WHEN e.event = 'tutorial_complete' THEN e.ts END) AS tutorial_complete,
           MIN(CASE WHEN e.event = 'first_match'       THEN e.ts END) AS first_match,
           MIN(CASE WHEN e.event = 'first_purchase'    THEN e.ts END) AS first_purchase
    FROM players p
    LEFT JOIN clean_events e ON e.player_id = p.player_id
    GROUP BY p.player_id
),
reached AS (
    SELECT player_id,
           1 AS s1,
           tutorial_start >= installed_at AS s2,
           tutorial_start >= installed_at AND tutorial_complete >= tutorial_start AS s3,
           tutorial_start >= installed_at AND tutorial_complete >= tutorial_start
               AND first_match >= tutorial_complete AS s4,
           tutorial_start >= installed_at AND tutorial_complete >= tutorial_start
               AND first_match >= tutorial_complete AND first_purchase >= first_match AS s5
    FROM firsts
),
steps AS (
    SELECT 1 AS step, 'install' AS name, SUM(s1) AS players FROM reached
    UNION ALL SELECT 2, 'tutorial_start',    SUM(COALESCE(s2, 0)) FROM reached
    UNION ALL SELECT 3, 'tutorial_complete', SUM(COALESCE(s3, 0)) FROM reached
    UNION ALL SELECT 4, 'first_match',       SUM(COALESCE(s4, 0)) FROM reached
    UNION ALL SELECT 5, 'first_purchase',    SUM(COALESCE(s5, 0)) FROM reached
)
SELECT step,
       name,
       players,
       ROUND(100.0 * players / FIRST_VALUE(players) OVER (ORDER BY step), 1)  AS pct_of_installs,
       ROUND(100.0 * players / LAG(players) OVER (ORDER BY step), 1)          AS pct_of_previous
FROM steps
ORDER BY step;
