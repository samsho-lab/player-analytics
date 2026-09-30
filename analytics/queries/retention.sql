-- Classic Day-N retention: of the players who installed at least N days
-- before the end of the data, what share opened the game on exactly day N?
--
-- Players whose day N hasn't happened yet are left out of the denominator.
-- Otherwise recent installs drag the number down for no real reason.

WITH activity AS (
    SELECT DISTINCT player_id, date(ts) AS day
    FROM clean_events
    WHERE event = 'session_start'
),
last_day AS (
    SELECT MAX(date(ts)) AS d FROM clean_events
),
days(n) AS (
    VALUES (1), (3), (7), (14)
)
SELECT d.n                                   AS day,
       COUNT(*)                              AS eligible,
       COUNT(a.player_id)                    AS retained,
       ROUND(100.0 * COUNT(a.player_id) / COUNT(*), 1) AS retention_pct
FROM players p
CROSS JOIN days d
CROSS JOIN last_day l
LEFT JOIN activity a
       ON a.player_id = p.player_id
      AND a.day = date(p.install_day, '+' || d.n || ' days')
WHERE date(p.install_day, '+' || d.n || ' days') <= l.d
GROUP BY d.n
ORDER BY d.n;
