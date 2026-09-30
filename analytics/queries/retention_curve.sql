-- Day-N retention for every day 1..14, split by experiment variant (for the chart).

WITH RECURSIVE days(n) AS (
    SELECT 1 UNION ALL SELECT n + 1 FROM days WHERE n < 14
),
activity AS (
    SELECT DISTINCT player_id, date(ts) AS day
    FROM clean_events
    WHERE event = 'session_start'
),
last_day AS (
    SELECT MAX(date(ts)) AS d FROM clean_events
)
SELECT p.variant,
       d.n AS day,
       ROUND(100.0 * COUNT(a.player_id) / COUNT(*), 2) AS retention_pct
FROM players p
CROSS JOIN days d
CROSS JOIN last_day l
LEFT JOIN activity a
       ON a.player_id = p.player_id
      AND a.day = date(p.install_day, '+' || d.n || ' days')
WHERE date(p.install_day, '+' || d.n || ' days') <= l.d
GROUP BY p.variant, d.n
ORDER BY p.variant, d.n;
